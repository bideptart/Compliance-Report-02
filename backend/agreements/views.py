from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DISPLAY_STATUS_CHOICES, EXPIRING_SOON_WINDOW_DAYS, Agreement
from .serializers import AgreementDetailSerializer, AgreementListSerializer, AgreementWriteSerializer

VALID_STATUS_FILTERS = {key for key, _ in DISPLAY_STATUS_CHOICES}
EXPIRY_PERIOD_DAYS = {"30": 30, "60": 60, "90": 90}


class AgreementPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


def _apply_filters(queryset, params):
    """Search + Agreement Type are cheap DB-level filters. Status and
    Expiry Period depend on the *computed* status (see
    Agreement.compute_status), which isn't a real column, so those are
    applied in Python after the DB-level filters narrow things down --
    same approach the Customers module's compliance_status filter uses.
    """
    search = (params.get("search") or "").strip()
    if search:
        queryset = queryset.filter(Q(agreement_id__icontains=search) | Q(customer__carrier__icontains=search))

    customer_id = (params.get("customer") or "").strip()
    if customer_id:
        queryset = queryset.filter(customer_id=customer_id)

    agreement_type = (params.get("agreement_type") or "").strip()
    if agreement_type:
        queryset = queryset.filter(agreement_type=agreement_type)

    agreements = list(queryset)

    status_filter = (params.get("status") or "").strip()
    if status_filter and status_filter in VALID_STATUS_FILTERS:
        agreements = [a for a in agreements if a.compute_status() == status_filter]

    expiry_period = (params.get("expiry_period") or "").strip()
    days = EXPIRY_PERIOD_DAYS.get(expiry_period)
    if days:
        today = timezone.localdate()
        horizon = today + timedelta(days=days)
        agreements = [a for a in agreements if a.expiry_date and today <= a.expiry_date <= horizon]

    return agreements


class AgreementListCreateView(APIView):
    """GET /api/agreements/?search=&agreement_type=&status=&expiry_period=&page=
    - every agreement, newest first, with search/filter support.

    POST /api/agreements/ - create a new agreement (multipart if a document
    is attached). agreement_id is generated server-side; the customer must
    already exist in the Customers database.
    """

    parser_classes = [MultiPartParser, FormParser]
    pagination_class = AgreementPagination

    def get(self, request, *args, **kwargs):
        queryset = Agreement.objects.select_related("customer").all()
        agreements = _apply_filters(queryset, request.query_params)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(agreements, request, view=self)
        serializer = AgreementListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = AgreementWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agreement = serializer.save()
        return Response(
            AgreementDetailSerializer(agreement, context={"request": request}).data,
            status=http_status.HTTP_201_CREATED,
        )


class AgreementDetailView(APIView):
    """GET /api/agreements/<id>/ - full detail, including the linked
    customer's real RMD/FCC company info.
    PATCH /api/agreements/<id>/ - edit (agreement_id is never editable --
    it's not even accepted as an input field, see AgreementWriteSerializer).
    """

    parser_classes = [MultiPartParser, FormParser]

    def get_object(self, pk):
        try:
            return Agreement.objects.select_related("customer", "previous_agreement").get(pk=pk)
        except Agreement.DoesNotExist:
            return None

    def get(self, request, pk, *args, **kwargs):
        agreement = self.get_object(pk)
        if agreement is None:
            return Response({"detail": "Agreement not found."}, status=http_status.HTTP_404_NOT_FOUND)
        return Response(AgreementDetailSerializer(agreement, context={"request": request}).data)

    def patch(self, request, pk, *args, **kwargs):
        agreement = self.get_object(pk)
        if agreement is None:
            return Response({"detail": "Agreement not found."}, status=http_status.HTTP_404_NOT_FOUND)

        serializer = AgreementWriteSerializer(agreement, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AgreementDetailSerializer(agreement, context={"request": request}).data)


class AgreementRenewView(APIView):
    """POST /api/agreements/<id>/renew/ - create a brand-new agreement
    (its own agreement_id) for the same customer, referencing this one as
    previous_agreement. Never happens automatically -- only when the user
    explicitly submits new effective/expiry dates (and optionally a new
    document) through this endpoint."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk, *args, **kwargs):
        try:
            original = Agreement.objects.get(pk=pk)
        except Agreement.DoesNotExist:
            return Response({"detail": "Agreement not found."}, status=http_status.HTTP_404_NOT_FOUND)

        data = {
            "customer": original.customer_id,
            "agreement_title": request.data.get("agreement_title") or original.agreement_title,
            "agreement_type": request.data.get("agreement_type") or original.agreement_type,
            "status": "active",
            "effective_date": request.data.get("effective_date"),
            "expiry_date": request.data.get("expiry_date") or None,
            "auto_renewal": request.data.get("auto_renewal", original.auto_renewal),
            "notes": request.data.get("notes", original.notes),
        }
        if request.FILES.get("document"):
            data["document"] = request.FILES["document"]

        serializer = AgreementWriteSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        renewed = serializer.save(previous_agreement=original)

        return Response(
            AgreementDetailSerializer(renewed, context={"request": request}).data,
            status=http_status.HTTP_201_CREATED,
        )


class AgreementTerminateView(APIView):
    """POST /api/agreements/<id>/terminate/ - manual, explicit termination
    with an optional reason. The record is never deleted, only its status
    changes -- kept for audit/history (see previous_agreement chain too)."""

    def post(self, request, pk, *args, **kwargs):
        try:
            agreement = Agreement.objects.get(pk=pk)
        except Agreement.DoesNotExist:
            return Response({"detail": "Agreement not found."}, status=http_status.HTTP_404_NOT_FOUND)

        agreement.status = "terminated"
        agreement.termination_reason = (request.data.get("termination_reason") or "").strip() or None
        agreement.save(update_fields=["status", "termination_reason", "updated_at"])

        return Response(AgreementDetailSerializer(agreement, context={"request": request}).data)


class AgreementStatsView(APIView):
    """GET /api/agreements/stats/ - real counts for the summary cards,
    computed fresh every time from the actual Agreement table (see
    Agreement.compute_status) -- never hardcoded, never stored."""

    def get(self, request, *args, **kwargs):
        agreements = list(Agreement.objects.all())
        statuses = [a.compute_status() for a in agreements]

        return Response(
            {
                "total": len(agreements),
                "active": statuses.count("active"),
                "expiring_soon": statuses.count("expiring_soon"),
                "expired": statuses.count("expired"),
                "draft": statuses.count("draft"),
                "pending_review": statuses.count("pending_review"),
                "terminated": statuses.count("terminated"),
                "expiring_soon_window_days": EXPIRING_SOON_WINDOW_DAYS,
            }
        )
