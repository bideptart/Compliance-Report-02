from rest_framework import serializers

from .models import Customer, normalize_carrier


class CustomerSerializer(serializers.ModelSerializer):
    """Carrier only -- Country and Provider are never modeled or exposed."""

    class Meta:
        model = Customer
        fields = ["id", "carrier"]

    def validate_carrier(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Carrier name is required.")

        key = normalize_carrier(value)
        existing = Customer.objects.filter(carrier_key=key)
        if self.instance is not None:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError("A customer with this carrier name already exists.")

        return value
