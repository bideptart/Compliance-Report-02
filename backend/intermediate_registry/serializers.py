from rest_framework import serializers

from .matching import find_registry_matches
from .models import ESCALATABLE_STATUSES, IntermediateRegistryRecord, RegistryEscalation
from .services import active_escalation_for

STATUS_LABELS = dict(IntermediateRegistryRecord._meta.get_field("status").choices)
ESCALATION_STATUS_LABELS = dict(RegistryEscalation._meta.get_field("status").choices)
PRIORITY_LABELS = dict(RegistryEscalation._meta.get_field("priority").choices)


class RegistryEscalationSerializer(serializers.ModelSerializer):
    """One real escalation -- always shows the company/customer/check it
    was raised against by reading straight through registry_record (never
    a duplicated copy of that data -- see models.RegistryEscalation)."""

    customer_id = serializers.IntegerField(source="registry_record.customer_id", read_only=True)
    customer_name = serializers.CharField(source="registry_record.customer.carrier", read_only=True)
    registry_id = serializers.CharField(source="registry_record.registry_id", read_only=True)
    verification_result_label = serializers.SerializerMethodField()
    priority_label = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = RegistryEscalation
        fields = [
            "id",
            "registry_record",
            "customer_id",
            "customer_name",
            "registry_id",
            "check_type",
            "verification_result",
            "verification_result_label",
            "issue",
            "priority",
            "priority_label",
            "assigned_to",
            "notes",
            "status",
            "status_label",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["registry_record", "check_type", "verification_result", "created_at", "updated_at"]

    def get_verification_result_label(self, obj):
        return STATUS_LABELS.get(obj.verification_result, obj.verification_result)

    def get_priority_label(self, obj):
        return PRIORITY_LABELS.get(obj.priority, obj.priority)

    def get_status_label(self, obj):
        return ESCALATION_STATUS_LABELS.get(obj.status, obj.status)


class RegistryListSerializer(serializers.ModelSerializer):
    """One row in the Registry Records table -- cheap: just the columns
    the table actually shows, using whatever status this customer's last
    check (import or Check Now) already computed."""

    customer_name = serializers.CharField(source="customer.carrier", read_only=True)
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = IntermediateRegistryRecord
        fields = [
            "id",
            "registry_id",
            "customer",
            "customer_name",
            "status",
            "status_label",
            "change_detected",
            "last_checked",
        ]

    def get_status_label(self, obj):
        return STATUS_LABELS.get(obj.status, obj.status)


class RegistryDetailSerializer(RegistryListSerializer):
    """Full registry record detail -- adds the matched entry's real
    registry data (Business Name/Address, Regulatory Contact) when
    status == "present", or the live list of ambiguous candidate business
    names when status == "review_required" (recomputed fresh from the CSV
    data every time, never a stale persisted list -- see matching.py).
    """

    business_name = serializers.SerializerMethodField()
    business_address = serializers.SerializerMethodField()
    regulatory_contact_name = serializers.SerializerMethodField()
    regulatory_contact_title = serializers.SerializerMethodField()
    regulatory_contact_telephone = serializers.SerializerMethodField()
    regulatory_contact_email = serializers.SerializerMethodField()
    review_candidates = serializers.SerializerMethodField()
    escalatable = serializers.SerializerMethodField()
    active_escalation = serializers.SerializerMethodField()
    latest_escalation = serializers.SerializerMethodField()

    class Meta(RegistryListSerializer.Meta):
        fields = RegistryListSerializer.Meta.fields + [
            "match_type",
            "business_name",
            "business_address",
            "regulatory_contact_name",
            "regulatory_contact_title",
            "regulatory_contact_telephone",
            "regulatory_contact_email",
            "review_candidates",
            "changes",
            "escalatable",
            "active_escalation",
            "latest_escalation",
        ]

    def get_business_name(self, obj):
        return obj.matched_entry.business_name if obj.matched_entry else None

    def get_business_address(self, obj):
        return obj.matched_entry.business_address if obj.matched_entry else None

    def get_regulatory_contact_name(self, obj):
        return obj.matched_entry.regulatory_contact_name if obj.matched_entry else None

    def get_regulatory_contact_title(self, obj):
        return obj.matched_entry.regulatory_contact_title if obj.matched_entry else None

    def get_regulatory_contact_telephone(self, obj):
        return obj.matched_entry.regulatory_contact_telephone if obj.matched_entry else None

    def get_regulatory_contact_email(self, obj):
        return obj.matched_entry.regulatory_contact_email if obj.matched_entry else None

    def get_review_candidates(self, obj):
        if obj.status != "review_required":
            return []
        matches, _match_type = find_registry_matches(obj.customer.carrier)
        return [entry.business_name for entry in matches]

    def get_escalatable(self, obj):
        return obj.status in ESCALATABLE_STATUSES

    def get_active_escalation(self, obj):
        escalation = active_escalation_for(obj)
        return RegistryEscalationSerializer(escalation).data if escalation else None

    def get_latest_escalation(self, obj):
        escalation = obj.escalations.order_by("-created_at").first()
        return RegistryEscalationSerializer(escalation).data if escalation else None
