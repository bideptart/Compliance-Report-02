from rest_framework import serializers

from customers.models import Customer
from verification.customer import get_customer_verification

from .models import TICKET_STATUS_CHOICES, TroubleTicket

STATUS_LABELS = dict(TICKET_STATUS_CHOICES)


class TicketListSerializer(serializers.ModelSerializer):
    """One row in the Trouble Tickets table -- cheap: just the customer's
    own carrier name, no live FCC/RMD lookups."""

    customer_name = serializers.CharField(source="customer.carrier", read_only=True)
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = TroubleTicket
        fields = [
            "id",
            "ticket_number",
            "customer",
            "customer_name",
            "date_opened",
            "problem",
            "status",
            "status_label",
            "noc_notified",
            "customer_notified",
            "date_closed",
            "created_at",
            "updated_at",
        ]

    def get_status_label(self, obj):
        return STATUS_LABELS.get(obj.status, obj.status)


class TicketDetailSerializer(TicketListSerializer):
    """Full ticket detail -- adds Resolution/Comments (deliberately left off
    the table, see trouble_tickets.views) plus the linked customer's real
    RMD/FCC company info, same as every other module that references a
    Customer."""

    customer_info = serializers.SerializerMethodField()

    class Meta(TicketListSerializer.Meta):
        fields = TicketListSerializer.Meta.fields + ["resolution_comments", "customer_info"]

    def get_customer_info(self, obj):
        result = get_customer_verification(obj.customer, allow_live_fcc_fetch=False)
        return {
            "company_name": result["company_name"],
            "country": result["country"],
            "frn": result["rmd_verification"].get("frn") or result["fcc_verification"].get("frn"),
        }


class TicketWriteSerializer(serializers.ModelSerializer):
    """Create/update payload -- ticket_number is never client-settable (see
    TroubleTicket.save/generate_ticket_number), and customer must be a real,
    already-imported Customer, never invented here."""

    class Meta:
        model = TroubleTicket
        fields = [
            "customer",
            "date_opened",
            "problem",
            "status",
            "noc_notified",
            "customer_notified",
            "resolution_comments",
            "date_closed",
        ]

    def validate_customer(self, value):
        if not Customer.objects.filter(pk=value.pk).exists():
            raise serializers.ValidationError("Customer not found.")
        return value

    def validate_problem(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Problem description is required.")
        return value

    def validate(self, attrs):
        # A ticket becoming Closed always needs a Date Closed -- auto-fill
        # with today rather than reject, so closing from a quick action
        # (no explicit date picked) still works; a ticket moving to any
        # other status is never forced to keep or lose a prior close date --
        # that's an explicit choice the caller makes by including or
        # omitting date_closed in the request.
        status = attrs.get("status") or getattr(self.instance, "status", None)
        date_closed = attrs.get("date_closed", serializers.empty)

        if status == "closed" and date_closed in (serializers.empty, None):
            from django.utils import timezone

            attrs["date_closed"] = timezone.localdate()

        return attrs
