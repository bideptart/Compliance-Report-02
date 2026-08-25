import re

from django.db import models


def normalize_carrier(value):
    """Lowercase, trimmed, whitespace-collapsed key used to detect duplicate
    Carrier names that only differ by case/spacing (e.g. "ABC Telecom" vs
    " abc  telecom ")."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.strip().lower())


class Customer(models.Model):
    """A unique Carrier imported from the actual salesperson CSV.

    Only ``Carrier`` is modeled -- ``Country`` and ``Provider`` are
    intentionally never imported, stored, or exposed here. The CSV can list
    the same carrier many times (once per country); ``carrier_key`` is a
    normalized form of the name used to enforce one row per real-world
    carrier, while ``carrier`` keeps a clean display version.
    """

    carrier = models.CharField(max_length=255, db_index=True)
    carrier_key = models.CharField(max_length=255, unique=True, db_index=True)

    # The real RMD/FCC record a person has confirmed is actually this
    # customer, once a name-based match turned out to be ambiguous (see the
    # dropdowns in CustomerVerificationPanel + CustomerLinkRecordsView).
    # Persisted so the resolution survives across visits -- everything that
    # computes this customer's verification (get_customer_verification /
    # get_customer_verifications_bulk) uses this as the default record
    # whenever the caller doesn't explicitly pass a different one to preview.
    linked_rmd_record = models.ForeignKey(
        "rmd.RmdFiling", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    linked_fcc_record = models.ForeignKey(
        "fcc499.Fcc499Filing", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    imported_at = models.DateTimeField(auto_now_add=True)
    updated_in_db_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["carrier"]
        indexes = [
            models.Index(fields=["carrier"]),
        ]

    def save(self, *args, **kwargs):
        self.carrier_key = normalize_carrier(self.carrier)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.carrier
