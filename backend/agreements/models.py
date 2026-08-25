from datetime import timedelta

from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from customers.models import Customer

# Only these are ever stored -- "Expiring Soon" and "Expired" are never a
# user choice, they're computed from expiry_date whenever status is
# "active" (see compute_status). Draft/Pending Review/Terminated are the
# only states a person sets directly, and Terminated is final: nothing
# ever recomputes over it.
AGREEMENT_STATUS_CHOICES = [
    ("draft", "Draft"),
    ("pending_review", "Pending Review"),
    ("active", "Active"),
    ("terminated", "Terminated"),
]

# The full set of statuses that can appear to a user (adds the two
# computed-only ones) -- used for validating the Status filter query param.
DISPLAY_STATUS_CHOICES = AGREEMENT_STATUS_CHOICES + [
    ("expiring_soon", "Expiring Soon"),
    ("expired", "Expired"),
]

AGREEMENT_TYPE_CHOICES = [
    ("customer_agreement", "Customer Agreement"),
    ("carrier_agreement", "Carrier Agreement"),
    ("service_agreement", "Service Agreement"),
    ("compliance_agreement", "Compliance Agreement"),
    ("other", "Other"),
]

ALLOWED_DOCUMENT_EXTENSIONS = ["pdf", "doc", "docx"]

EXPIRING_SOON_WINDOW_DAYS = 30


def generate_agreement_id():
    """AGR-0001, AGR-0002, ... -- sequential and collision-safe even if a
    row was deleted in the middle."""
    next_num = Agreement.objects.count() + 1
    candidate = f"AGR-{next_num:04d}"
    while Agreement.objects.filter(agreement_id=candidate).exists():
        next_num += 1
        candidate = f"AGR-{next_num:04d}"
    return candidate


class Agreement(models.Model):
    """A real customer/compliance agreement -- linked to an existing
    Customer (never a duplicated/invented name), with the uploaded
    document stored on disk (see MEDIA_ROOT) and only its reference kept
    here. Nothing here is ever pre-seeded; every row reflects an agreement
    someone actually created through this module."""

    agreement_id = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="agreements")

    agreement_title = models.CharField(max_length=255)
    agreement_type = models.CharField(max_length=30, choices=AGREEMENT_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=AGREEMENT_STATUS_CHOICES, default="draft")

    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    auto_renewal = models.BooleanField(default=False)

    document = models.FileField(
        upload_to="agreements/%Y/%m/",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_DOCUMENT_EXTENSIONS)],
    )
    notes = models.TextField(blank=True, null=True)

    termination_reason = models.TextField(blank=True, null=True)
    previous_agreement = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="renewals"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.agreement_id:
            self.agreement_id = generate_agreement_id()
        super().save(*args, **kwargs)

    def compute_status(self):
        """The status actually shown to the user. Draft/Pending Review/
        Terminated are exactly what was stored -- never recomputed. Active
        is re-derived from the real expiry_date every time, using actual
        date objects (never string comparison), so it can read as Active,
        Expiring Soon, or Expired without a background job rewriting the
        stored value."""
        if self.status in ("draft", "pending_review", "terminated"):
            return self.status
        if not self.expiry_date:
            return "active"
        today = timezone.localdate()
        if self.expiry_date < today:
            return "expired"
        if self.expiry_date <= today + timedelta(days=EXPIRING_SOON_WINDOW_DAYS):
            return "expiring_soon"
        return "active"

    def __str__(self):
        return f"{self.agreement_id} - {self.customer.carrier}"
