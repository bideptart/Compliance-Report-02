from django.db import models


class Fcc499Filing(models.Model):
    """A cached FCC Form 499 record.

    Fields mirror exactly what ``fcc499.service.parse_fcc_499_html`` is able
    to extract from the official FCC Form 499 detail page -- no invented
    fields. Acts as a local cache: once a company has been successfully
    looked up, it is stored here so future searches for the same filer
    don't re-scrape the FCC site.
    """

    filer_id = models.CharField(
        max_length=20, unique=True, db_index=True,
        help_text="499 Filer ID from the FCC record",
    )
    legal_name = models.CharField(max_length=500, db_index=True)
    doing_business_as = models.CharField(max_length=500, null=True, blank=True)
    usf_contributor = models.CharField(max_length=20, null=True, blank=True)
    cores_id = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    registration_current_as_of = models.CharField(max_length=50, null=True, blank=True)

    headquarters_address = models.CharField(max_length=500, null=True, blank=True)
    headquarters_city = models.CharField(max_length=150, null=True, blank=True)
    headquarters_state = models.CharField(max_length=50, null=True, blank=True)
    headquarters_zip = models.CharField(max_length=20, null=True, blank=True)

    customer_phone = models.CharField(max_length=50, null=True, blank=True)
    fcc_registration_information = models.CharField(max_length=255, null=True, blank=True)

    search_company_name = models.CharField(
        max_length=500, db_index=True,
        help_text="The company name that was searched to find this filing",
    )
    search_url = models.URLField(max_length=1000, null=True, blank=True)
    detail_url = models.URLField(
        max_length=1000, null=True, blank=True,
        help_text="Official FCC Form 499 detail page for this filer",
    )

    fetched_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["legal_name"]
        indexes = [
            models.Index(fields=["legal_name"]),
            models.Index(fields=["filer_id"]),
            models.Index(fields=["search_company_name"]),
        ]

    def __str__(self):
        return f"{self.legal_name} (Filer ID {self.filer_id})"
