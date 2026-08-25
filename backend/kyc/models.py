from django.core.validators import FileExtensionValidator
from django.db import models

from customers.models import Customer

STATUS_CHOICES = [
    ("pending", "Pending Review"),
    ("verified", "Verified"),
    ("flagged", "Flagged"),
]

ALLOWED_EXTENSIONS = ["pdf", "png", "jpg", "jpeg"]


class KycDocument(models.Model):
    """A real uploaded KYC document for a customer -- the file itself is
    stored on disk (see MEDIA_ROOT), everything else here is metadata about
    that upload. No document is ever invented; this table only ever
    reflects files someone actually uploaded through the KYC page."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="kyc_documents")
    file = models.FileField(
        upload_to="kyc_documents/%Y/%m/",
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_EXTENSIONS)],
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    reviewed_by = models.CharField(max_length=100, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.customer.carrier} - {self.file.name}"
