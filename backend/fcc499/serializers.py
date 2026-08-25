from rest_framework import serializers

from .models import Fcc499Filing


class Fcc499SearchResultSerializer(serializers.ModelSerializer):
    """Search result / history row: real FCC Form 499 fields + Official Link."""

    class Meta:
        model = Fcc499Filing
        fields = [
            "id",
            "filer_id",
            "legal_name",
            "doing_business_as",
            "usf_contributor",
            "cores_id",
            "registration_current_as_of",
            "detail_url",
        ]


class Fcc499DetailSerializer(serializers.ModelSerializer):
    """Full stored representation of a single FCC Form 499 filing."""

    class Meta:
        model = Fcc499Filing
        fields = "__all__"
