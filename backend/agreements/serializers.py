from rest_framework import serializers

from customers.models import Customer
from verification.customer import get_customer_verification

from .models import AGREEMENT_STATUS_CHOICES, AGREEMENT_TYPE_CHOICES, Agreement

STATUS_LABELS = dict(AGREEMENT_STATUS_CHOICES) | {
    "expiring_soon": "Expiring Soon",
    "expired": "Expired",
}
TYPE_LABELS = dict(AGREEMENT_TYPE_CHOICES)


class AgreementListSerializer(serializers.ModelSerializer):
    """One row in the Agreements table -- cheap: no live FCC/RMD lookups,
    just the customer's own carrier name."""

    customer_name = serializers.CharField(source="customer.carrier", read_only=True)
    status = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    agreement_type_label = serializers.SerializerMethodField()
    document_url = serializers.SerializerMethodField()
    document_name = serializers.SerializerMethodField()

    class Meta:
        model = Agreement
        fields = [
            "id",
            "agreement_id",
            "customer",
            "customer_name",
            "agreement_title",
            "agreement_type",
            "agreement_type_label",
            "status",
            "status_label",
            "effective_date",
            "expiry_date",
            "auto_renewal",
            "document_url",
            "document_name",
            "created_at",
            "updated_at",
        ]

    def get_status(self, obj):
        return obj.compute_status()

    def get_status_label(self, obj):
        return STATUS_LABELS.get(obj.compute_status(), obj.compute_status())

    def get_agreement_type_label(self, obj):
        return TYPE_LABELS.get(obj.agreement_type, obj.agreement_type)

    def get_document_url(self, obj):
        if not obj.document:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.document.url) if request else obj.document.url

    def get_document_name(self, obj):
        return obj.document.name.rsplit("/", 1)[-1] if obj.document else None


class AgreementDetailSerializer(AgreementListSerializer):
    """Full agreement detail -- adds the linked customer's real RMD/FCC
    company info (same verification package every other module uses, so
    this agrees with what the Customers module itself shows) plus notes,
    termination reason, and the renewal chain."""

    customer_info = serializers.SerializerMethodField()
    previous_agreement_id = serializers.CharField(source="previous_agreement.agreement_id", read_only=True)

    class Meta(AgreementListSerializer.Meta):
        fields = AgreementListSerializer.Meta.fields + [
            "notes",
            "termination_reason",
            "previous_agreement",
            "previous_agreement_id",
            "customer_info",
        ]

    def get_customer_info(self, obj):
        result = get_customer_verification(obj.customer, allow_live_fcc_fetch=False)
        return {
            "company_name": result["company_name"],
            "country": result["country"],
            "frn": result["rmd_verification"].get("frn") or result["fcc_verification"].get("frn"),
        }


class AgreementWriteSerializer(serializers.ModelSerializer):
    """Create/update payload -- agreement_id is never client-settable (see
    Agreement.save/generate_agreement_id), and customer must be a real,
    already-imported Customer, never invented here."""

    class Meta:
        model = Agreement
        fields = [
            "customer",
            "agreement_title",
            "agreement_type",
            "status",
            "effective_date",
            "expiry_date",
            "auto_renewal",
            "document",
            "notes",
        ]
        extra_kwargs = {"document": {"required": False}}

    def validate_customer(self, value):
        if not Customer.objects.filter(pk=value.pk).exists():
            raise serializers.ValidationError("Customer not found.")
        return value

    def validate_agreement_title(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Agreement title is required.")
        return value
