from django.db.models import Q
from rest_framework import status as http_status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TICKET_STATUS_CHOICES, TroubleTicket
from .serializers import TicketDetailSerializer, TicketListSerializer, TicketWriteSerializer

VALID_STATUS_FILTERS = {key for key, _ in TICKET_STATUS_CHOICES}


class TicketPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


def _apply_filters(queryset, params):
    search = (params.get("search") or "").strip()
    if search:
        queryset = queryset.filter(Q(ticket_number__icontains=search) | Q(customer__carrier__icontains=search))

    customer_id = (params.get("customer") or "").strip()
    if customer_id:
        queryset = queryset.filter(customer_id=customer_id)

    status_filter = (params.get("status") or "").strip()
    if status_filter and status_filter in VALID_STATUS_FILTERS:
        queryset = queryset.filter(status=status_filter)

    date_from = (params.get("date_from") or "").strip()
    if date_from:
        queryset = queryset.filter(date_opened__gte=date_from)

    date_to = (params.get("date_to") or "").strip()
    if date_to:
        queryset = queryset.filter(date_opened__lte=date_to)

    return queryset


class TicketListCreateView(APIView):
    """GET /api/tickets/?search=&status=&date_from=&date_to=&customer=&page=
    - every ticket, newest first, with search/filter support.

    POST /api/tickets/ - create a new ticket. ticket_number is generated
    server-side; the customer must already exist in the Customers database.
    """

    pagination_class = TicketPagination

    def get(self, request, *args, **kwargs):
        queryset = TroubleTicket.objects.select_related("customer").all()
        queryset = _apply_filters(queryset, request.query_params)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = TicketListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = TicketWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save()
        return Response(TicketDetailSerializer(ticket).data, status=http_status.HTTP_201_CREATED)


class TicketDetailView(APIView):
    """GET /api/tickets/<id>/ - full detail, including the linked
    customer's real RMD/FCC company info and Resolution/Comments.
    PATCH /api/tickets/<id>/ - edit (ticket_number is never editable -- it's
    not even accepted as an input field, see TicketWriteSerializer).
    """

    def get_object(self, pk):
        try:
            return TroubleTicket.objects.select_related("customer").get(pk=pk)
        except TroubleTicket.DoesNotExist:
            return None

    def get(self, request, pk, *args, **kwargs):
        ticket = self.get_object(pk)
        if ticket is None:
            return Response({"detail": "Ticket not found."}, status=http_status.HTTP_404_NOT_FOUND)
        return Response(TicketDetailSerializer(ticket).data)

    def patch(self, request, pk, *args, **kwargs):
        ticket = self.get_object(pk)
        if ticket is None:
            return Response({"detail": "Ticket not found."}, status=http_status.HTTP_404_NOT_FOUND)

        serializer = TicketWriteSerializer(ticket, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TicketDetailSerializer(ticket).data)


class TicketStatsView(APIView):
    """GET /api/tickets/stats/ - real counts for the summary cards, computed
    fresh every time from the actual TroubleTicket table -- never
    hardcoded, never stored."""

    def get(self, request, *args, **kwargs):
        tickets = TroubleTicket.objects.all()

        return Response(
            {
                "total": tickets.count(),
                "open": tickets.filter(status="open").count(),
                "in_progress": tickets.filter(status="in_progress").count(),
                "resolved": tickets.filter(status="resolved").count(),
                "closed": tickets.filter(status="closed").count(),
            }
        )
