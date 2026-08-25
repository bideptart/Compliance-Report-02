from django.db import models

from customers.models import Customer

# Every real Customer/Carrier's presence in the imported Intermediate
# Provider Registry CSV (see IntermediateRegistryEntry) -- never a guess.
# "review_required" means the company name matched more than one real CSV
# entry and the system could not confidently pick one (see matching.py);
# it is never collapsed into "present" by picking the first candidate.
STATUS_CHOICES = [
    ("present", "Present"),
    ("not_present", "Not Present"),
    ("review_required", "Review Required"),
]


def generate_registry_id():
    """IR-000001, IR-000002, ... -- sequential and collision-safe even if a
    row was deleted in the middle (mirrors Agreement.generate_agreement_id
    and TroubleTicket.generate_ticket_number)."""
    next_num = IntermediateRegistryRecord.objects.count() + 1
    candidate = f"IR-{next_num:06d}"
    while IntermediateRegistryRecord.objects.filter(registry_id=candidate).exists():
        next_num += 1
        candidate = f"IR-{next_num:06d}"
    return candidate


class IntermediateRegistryEntry(models.Model):
    """One real row from the FCC's own official Intermediate Provider
    Registry open data (opendata.fcc.gov, dataset a6ec-cry4 -- see
    fcc_open_data.py) -- a lookup/reference table, never displayed on its
    own and never treated as a Customer. Only the fields this feature
    actually uses are stored (see
    management/commands/import_intermediate_registry.py); every other
    field the API returns (Previous Business Names, States Serviced,
    Rural Call Completion contact, ...) is intentionally never imported.
    """

    business_name = models.CharField(max_length=500, db_index=True)
    business_address = models.TextField(null=True, blank=True)
    regulatory_contact_name = models.CharField(max_length=255, null=True, blank=True)
    regulatory_contact_title = models.CharField(max_length=255, null=True, blank=True)
    regulatory_contact_telephone = models.CharField(max_length=50, null=True, blank=True)
    regulatory_contact_email = models.CharField(max_length=255, null=True, blank=True)

    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["business_name"])]

    def __str__(self):
        return self.business_name


class IntermediateRegistryRecord(models.Model):
    """One real Customer's match status against the Intermediate Provider
    Registry CSV -- the Intermediate Registry module never invents or
    duplicates a customer, it only observes one that already exists (see
    services.ensure_registry_records_exist). Every real Customer gets
    exactly one of these; unrelated businesses from the CSV that aren't
    also a real Customer never get a row here and are never shown.

    matched_entry is set only when status == "present" (an unambiguous
    single match). For "review_required", the candidate business names are
    recomputed live from the CSV (see matching.find_registry_matches)
    rather than persisted, so they're never stale relative to the current
    CSV import.
    """

    registry_id = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name="registry_record")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="not_present")
    matched_entry = models.ForeignKey(
        IntermediateRegistryEntry, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # "exact_normalized" or "broadened" -- see matching.py. Null until the
    # first real check runs.
    match_type = models.CharField(max_length=20, null=True, blank=True)

    # Whether this customer's registry info (status, business name/address,
    # regulatory contact) differs from what the *previous* check found --
    # see services._build_snapshot / _detect_changes. current_snapshot /
    # previous_snapshot hold the actual field values being compared, kept
    # as plain denormalized data (not a live FK read) specifically because
    # matched_entry can go stale/null the moment a fresh CSV re-import
    # deletes the old IntermediateRegistryEntry rows -- the snapshot is
    # what survives that to make the next check's diff meaningful.
    change_detected = models.BooleanField(default=False)
    changes = models.JSONField(default=list, blank=True)
    current_snapshot = models.JSONField(null=True, blank=True)
    previous_snapshot = models.JSONField(null=True, blank=True)

    last_checked = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Registry ID is a plain sequential IR-000001, IR-000002, ...
        # label -- the table should read in that same order, not jump
        # around by whichever record was checked/updated most recently.
        ordering = ["registry_id"]

    def save(self, *args, **kwargs):
        if not self.registry_id:
            self.registry_id = generate_registry_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.registry_id} - {self.customer.carrier}"


# The two "problem" statuses a registry check can come back with -- the
# workflow's own "FLAGGED or FAILED" language, mapped onto the real
# statuses this feature actually computes (see matching.classify_matches):
# "not_present" (the customer couldn't be found at all) and
# "review_required" (an ambiguous match that needs a person to resolve).
# "present" is the clean pass -- never escalatable. Exposed here (not
# views.py) so both the model's own validation and any other code that
# needs "is this status escalatable" agree on one real definition.
ESCALATABLE_STATUSES = {"not_present", "review_required"}

ESCALATION_STATUS_CHOICES = [
    ("open", "Open"),
    ("in_review", "In Review"),
    ("resolved", "Resolved"),
    ("rejected", "Rejected"),
]

# Active = still needs attention -- see services.has_active_escalation,
# which uses this to block a duplicate escalation on the same check.
ACTIVE_ESCALATION_STATUSES = {"open", "in_review"}

PRIORITY_CHOICES = [
    ("low", "Low"),
    ("medium", "Medium"),
    ("high", "High"),
    ("critical", "Critical"),
]


class RegistryEscalation(models.Model):
    """One real escalation raised against one Intermediate Registry check
    result -- created only by an explicit user action (see
    views.RegistryEscalationCreateView), never automatically. Always
    linked to the registry_record it was raised against (and, through it,
    to the real Customer/company) -- Company Name and Customer ID are
    never duplicated onto this model, always read live through that FK,
    so there is exactly one source of truth for who the escalation is
    about.

    check_type / verification_result are a snapshot of what the record's
    status actually was at the moment this escalation was created -- kept
    here (not just read live off registry_record.status) so the
    escalation still honestly shows what caused it even if a later check
    changes the record's current status.
    """

    registry_record = models.ForeignKey(
        IntermediateRegistryRecord, on_delete=models.CASCADE, related_name="escalations"
    )

    check_type = models.CharField(max_length=50, default="Intermediate Registry")
    verification_result = models.CharField(max_length=20, choices=STATUS_CHOICES)

    issue = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")
    assigned_to = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=ESCALATION_STATUS_CHOICES, default="open")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Escalation for {self.registry_record.registry_id} ({self.status})"
