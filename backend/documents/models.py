from django.core.validators import FileExtensionValidator
from django.db import models

from customers.models import Customer

ALLOWED_EXTENSIONS = ["pdf", "png", "jpg", "jpeg", "doc", "docx", "xls", "xlsx", "csv", "txt"]

DOCUMENT_TYPE_CHOICES = [
    ("document", "Document"),
    ("tech_form", "Tech Form"),
]


class Document(models.Model):
    """A real uploaded compliance/customer document -- the file itself is
    stored on disk (see MEDIA_ROOT). Multiple documents can be uploaded in
    one batch (see documents.views), each becoming its own row here so the
    library always reflects exactly what was actually uploaded.

    document_type separates the Customer Detail page's "Documents" card
    from its "Tech Form" card -- same upload mechanism and storage, just a
    different category tag, so the two counts/lists never mix."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(
        upload_to="documents/%Y/%m/",
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_EXTENSIONS)],
    )
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, default="document")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.customer.carrier} - {self.file.name}"
