from rest_framework import serializers

from customers.models import Customer

from .models import KycDocument


class KycDocumentSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.carrier", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = KycDocument
        fields = [
            "id",
            "customer",
            "customer_name",
            "file",
            "file_url",
            "file_name",
            "status",
            "status_label",
            "reviewed_by",
            "uploaded_at",
            "updated_at",
        ]
        read_only_fields = ["status", "reviewed_by", "uploaded_at", "updated_at"]
        extra_kwargs = {"file": {"write_only": True}}

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not obj.file:
            return None
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url

    def get_file_name(self, obj):
        return obj.file.name.rsplit("/", 1)[-1] if obj.file else None

    def validate_customer(self, value):
        if not Customer.objects.filter(pk=value.pk).exists():
            raise serializers.ValidationError("Customer not found.")
        return value
