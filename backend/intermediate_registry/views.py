from django.db.models import Q
from rest_framework import status as http_status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    ESCALATABLE_STATUSES,
    ESCALATION_STATUS_CHOICES,
    STATUS_CHOICES,
    IntermediateRegistryRecord,
    RegistryEscalation,
)
from .serializers import RegistryDetailSerializer, RegistryEscalationSerializer, RegistryListSerializer
from .services import active_escalation_for, check_customer, ensure_registry_records_exist

VALID_STATUSES = {key for key, _ in STATUS_CHOICES}
VALID_ESCALATION_STATUSES = {key for key, _ in ESCALATION_STATUS_CHOICES}


class RegistryPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


def _apply_filters(queryset, params):
    search = (params.get("search") or "").strip()
    if search:
        queryset = queryset.filter(Q(customer__carrier__icontains=search) | Q(registry_id__icontains=search))

    status_filter = (params.get("status") or "").strip()
    if status_filter and status_filter in VALID_STATUSES:
        queryset = queryset.filter(status=status_filter)

    return queryset


class RegistryListView(APIView):
    """GET /api/intermediate-registry/?search=&status=&page=

    Every real Customer is represented here -- any customer missing a
    registry record is backfilled (see services.ensure_registry_records_exist)
    before listing, so a newly imported/created customer always appears
    without needing a manual step. Never shows a business from the CSV
    that isn't also a real Customer.
    """

    pagination_class = RegistryPagination

    def get(self, request, *args, **kwargs):
        ensure_registry_records_exist()

        queryset = IntermediateRegistryRecord.objects.select_related("customer").all()
        queryset = _apply_filters(queryset, request.query_params)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = RegistryListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class RegistryStatsView(APIView):
    """GET /api/intermediate-registry/stats/ - real counts for the summary
    cards, computed fresh every time from the actual registry table --
    never hardcoded, never stored."""

    def get(self, request, *args, **kwargs):
        ensure_registry_records_exist()

        records = IntermediateRegistryRecord.objects.all()

        return Response(
            {
                "total_customers": records.count(),
                "present": records.filter(status="present").count(),
                "not_present": records.filter(status="not_present").count(),
                "review_required": records.filter(status="review_required").count(),
            }
        )


class RegistryDetailView(APIView):
    """GET /api/intermediate-registry/<id>/ - full detail for one registry
    record, including the matched entry's registry/contact data (if
    present) or the live list of ambiguous candidates (if review
    required)."""

    def get_object(self, pk):
        try:
            return (
                IntermediateRegistryRecord.objects.select_related("customer", "matched_entry").get(pk=pk)
            )
        except IntermediateRegistryRecord.DoesNotExist:
            return None

    def get(self, request, pk, *args, **kwargs):
        record = self.get_object(pk)
        if record is None:
            return Response({"detail": "Registry record not found."}, status=http_status.HTTP_404_NOT_FOUND)
        return Response(RegistryDetailSerializer(record).data)


class RegistryCheckNowView(APIView):
    """POST /api/intermediate-registry/<id>/check/ - re-runs the real
    Intermediate Provider Registry match for exactly this one customer
    against the currently-imported CSV data, then returns the updated
    record. Reuses the exact same matching pipeline the bulk CSV-import
    recheck uses (see services.py) -- never a separate/duplicated path.
    """

    def post(self, request, pk, *args, **kwargs):
        try:
            record = IntermediateRegistryRecord.objects.select_related("customer").get(pk=pk)
        except IntermediateRegistryRecord.DoesNotExist:
            return Response({"detail": "Registry record not found."}, status=http_status.HTTP_404_NOT_FOUND)

        updated = check_customer(record.customer)
        return Response(RegistryDetailSerializer(updated).data)


class RegistryEscalationCreateView(APIView):
    """POST /api/intermediate-registry/<record_id>/escalations/ - creates
    a real escalation against this registry check, only by explicit user
    action (never automatic). Company Name and Customer ID are never
    accepted from the request -- always the real registry_record's own
    customer, so an escalation can never be linked to the wrong company.

    Refuses to create a second active (Open/In Review) escalation for the
    same check -- returns the existing one instead (see
    services.active_escalation_for) so the frontend can show/link it
    rather than silently failing.
    """

    def post(self, request, record_id, *args, **kwargs):
        try:
            record = IntermediateRegistryRecord.objects.select_related("customer").get(pk=record_id)
        except IntermediateRegistryRecord.DoesNotExist:
            return Response({"detail": "Registry record not found."}, status=http_status.HTTP_404_NOT_FOUND)

        if record.status not in ESCALATABLE_STATUSES:
            return Response(
                {"detail": "This registry check is not in a state that requires escalation."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        existing = active_escalation_for(record)
        if existing is not None:
            return Response(
                {
                    "detail": "An active escalation already exists for this registry check.",
                    "escalation": RegistryEscalationSerializer(existing).data,
                },
                status=http_status.HTTP_409_CONFLICT,
            )

        issue = (request.data.get("issue") or "").strip()
        if not issue:
            return Response({"detail": "Issue / Reason is required."}, status=http_status.HTTP_400_BAD_REQUEST)

        priority = (request.data.get("priority") or "medium").strip()
        if priority not in {"low", "medium", "high", "critical"}:
            priority = "medium"

        escalation = RegistryEscalation.objects.create(
            registry_record=record,
            check_type="Intermediate Registry",
            verification_result=record.status,
            issue=issue,
            priority=priority,
            assigned_to=(request.data.get("assigned_to") or "").strip() or None,
            notes=(request.data.get("notes") or "").strip() or None,
            status="open",
        )
        return Response(RegistryEscalationSerializer(escalation).data, status=http_status.HTTP_201_CREATED)


class RegistryEscalationDetailView(APIView):
    """PATCH /api/intermediate-registry/escalations/<id>/ - updates an
    existing escalation's status (Open/In Review/Resolved/Rejected) and/or
    priority, assigned-to, and notes. The escalation stays linked to
    exactly the same registry check/customer it was created against --
    that link is never editable here.
    """

    def get_object(self, pk):
        try:
            return RegistryEscalation.objects.select_related("registry_record", "registry_record__customer").get(pk=pk)
        except RegistryEscalation.DoesNotExist:
            return None

    def get(self, request, pk, *args, **kwargs):
        escalation = self.get_object(pk)
        if escalation is None:
            return Response({"detail": "Escalation not found."}, status=http_status.HTTP_404_NOT_FOUND)
        return Response(RegistryEscalationSerializer(escalation).data)

    def patch(self, request, pk, *args, **kwargs):
        escalation = self.get_object(pk)
        if escalation is None:
            return Response({"detail": "Escalation not found."}, status=http_status.HTTP_404_NOT_FOUND)

        if "status" in request.data:
            new_status = (request.data.get("status") or "").strip()
            if new_status not in VALID_ESCALATION_STATUSES:
                return Response({"detail": "Invalid escalation status."}, status=http_status.HTTP_400_BAD_REQUEST)
            escalation.status = new_status

        if "priority" in request.data:
            priority = (request.data.get("priority") or "").strip()
            if priority in {"low", "medium", "high", "critical"}:
                escalation.priority = priority

        if "assigned_to" in request.data:
            escalation.assigned_to = (request.data.get("assigned_to") or "").strip() or None

        if "notes" in request.data:
            escalation.notes = (request.data.get("notes") or "").strip() or None

        escalation.save()
        return Response(RegistryEscalationSerializer(escalation).data)
