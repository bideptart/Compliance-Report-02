from rest_framework import serializers

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.carrier", read_only=True)
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "customer",
            "customer_name",
            "file",
            "file_url",
            "file_name",
            "document_type",
            "uploaded_at",
        ]
        extra_kwargs = {"file": {"write_only": True}}

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not obj.file:
            return None
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url

    def get_file_name(self, obj):
        return obj.file.name.rsplit("/", 1)[-1] if obj.file else None
