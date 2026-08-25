from rest_framework import serializers

from .compliance import compute_operational_status
from .models import RmdFiling


class RmdFilingListSerializer(serializers.ModelSerializer):
    """Compact representation used for list results."""

    class Meta:
        model = RmdFiling
        fields = [
            "id",
            "number",
            "frn",
            "business_name",
            "country",
            "implementation",
            "last_updated",
            "last_recertified",
            "filing_url",
        ]


class RmdSearchResultSerializer(serializers.ModelSerializer):
    """Search result row: Company Name, Country of Origin, FRN, Operational
    Status, and the real official filing link.

    ``operational_status`` is computed, not stored -- see rmd.compliance.
    The FCC cross-check (``fcc_verification`` / ``frn_verification``) is
    attached separately by the view, using the central ``verification``
    package shared with the FCC Compliance and Customers modules.
    """

    country_of_origin = serializers.CharField(source="country")
    operational_status = serializers.SerializerMethodField()

    class Meta:
        model = RmdFiling
        fields = [
            "id",
            "number",
            "business_name",
            "country_of_origin",
            "frn",
            "operational_status",
            "last_recertified",
            "filing_url",
        ]

    def get_operational_status(self, obj):
        return compute_operational_status(obj.last_recertified)


class RmdFilingDetailSerializer(serializers.ModelSerializer):
    """Full representation for a single RMD record.

    Includes the computed ``operational_status`` (see rmd.compliance) so the
    frontend can refresh a previously-fetched record's status from this same
    endpoint without duplicating the threshold logic in JS.
    """

    operational_status = serializers.SerializerMethodField()

    class Meta:
        model = RmdFiling
        fields = "__all__"

    def get_operational_status(self, obj):
        return compute_operational_status(obj.last_recertified)
