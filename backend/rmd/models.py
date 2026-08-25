from django.db import models


class RmdFiling(models.Model):
    """A single Robocall Mitigation Database filing record.

    Fields mirror the actual columns of the FCC RMD export CSV. ``sys_id`` is
    not a CSV column itself -- it is parsed out of the ``filing_url`` query
    string, since it is the stable identifier the FCC/ServiceNow system uses
    for that filing.
    """

    number = models.CharField(
        max_length=32, unique=True, db_index=True,
        help_text="RMD identifier, e.g. RMD0001410",
    )
    sys_id = models.CharField(
        max_length=64, unique=True, null=True, blank=True, db_index=True,
        help_text="ServiceNow sys_id parsed from filing_url",
    )
    frn = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    business_name = models.CharField(max_length=500, null=True, blank=True, db_index=True)
    business_address = models.TextField(null=True, blank=True)
    foreign_voice_provider = models.CharField(max_length=10, null=True, blank=True)
    country = models.CharField(max_length=150, null=True, blank=True)
    other_frns = models.TextField(null=True, blank=True)
    other_dba_names = models.TextField(null=True, blank=True)
    previous_dba_names = models.TextField(null=True, blank=True)
    robocall_mitigation_contact_name = models.CharField(max_length=255, null=True, blank=True)
    contact_title = models.CharField(max_length=255, null=True, blank=True)
    contact_department = models.CharField(max_length=255, null=True, blank=True)
    contact_business_address = models.TextField(null=True, blank=True)
    contact_country = models.CharField(max_length=150, null=True, blank=True)
    contact_telephone_number = models.CharField(max_length=50, null=True, blank=True)
    contact_phone_extension = models.CharField(max_length=20, null=True, blank=True)
    implementation = models.CharField(max_length=255, null=True, blank=True)
    voice_service_provider_choice = models.CharField(max_length=10, null=True, blank=True)
    gateway_provider_choice = models.CharField(max_length=10, null=True, blank=True)
    intermediate_provider_choice = models.CharField(max_length=10, null=True, blank=True)
    last_updated = models.DateField(null=True, blank=True)
    last_recertified = models.DateField(null=True, blank=True)
    filing_url = models.URLField(max_length=1000, null=True, blank=True)

    imported_at = models.DateTimeField(auto_now_add=True)
    updated_in_db_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["business_name"]
        indexes = [
            models.Index(fields=["business_name"]),
            models.Index(fields=["frn"]),
            models.Index(fields=["number"]),
        ]

    def __str__(self):
        return f"{self.number} - {self.business_name or 'Unknown business'}"
