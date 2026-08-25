"""Applies the Intermediate Provider Registry matching pipeline (see
matching.py) to real Customers -- registers customers into the registry
(one record each, never duplicated) and stamps each with its current
Present/Not Present/Review Required status, plus whether that status or
registry data changed since the *previous* check (see _detect_changes).
Deliberately thin: all the actual name-matching lives in matching.py; this
module only orchestrates it against the real Customer table and persists
the result.
"""
from django.utils import timezone

from customers.models import Customer

from .matching import classify_matches, find_registry_matches, find_registry_matches_bulk
from .models import ACTIVE_ESCALATION_STATUSES, IntermediateRegistryRecord

# The real, denormalized fields compared between one check and the next --
# see models.IntermediateRegistryRecord.current_snapshot/changes. Never a
# second source of truth: always built fresh from the same match result
# classify_matches/find_registry_matches already computed.
_SNAPSHOT_FIELDS = [
    ("status", "Status"),
    ("business_name", "Business Name"),
    ("business_address", "Business Address"),
    ("regulatory_contact_name", "Regulatory Contact Name"),
    ("regulatory_contact_title", "Regulatory Contact Title"),
    ("regulatory_contact_telephone", "Regulatory Contact Telephone"),
    ("regulatory_contact_email", "Regulatory Contact Email"),
]


def _build_snapshot(status, matched_entry):
    return {
        "status": status,
        "business_name": matched_entry.business_name if matched_entry else None,
        "business_address": matched_entry.business_address if matched_entry else None,
        "regulatory_contact_name": matched_entry.regulatory_contact_name if matched_entry else None,
        "regulatory_contact_title": matched_entry.regulatory_contact_title if matched_entry else None,
        "regulatory_contact_telephone": matched_entry.regulatory_contact_telephone if matched_entry else None,
        "regulatory_contact_email": matched_entry.regulatory_contact_email if matched_entry else None,
    }


def _detect_changes(previous_snapshot, new_snapshot):
    """(change_detected, changes) comparing the prior stored snapshot
    against the just-computed one. Returns no changes on a record's very
    first check (nothing real to compare against yet)."""
    if not previous_snapshot:
        return False, []

    changes = []
    for field, label in _SNAPSHOT_FIELDS:
        previous_value = previous_snapshot.get(field)
        current_value = new_snapshot.get(field)
        if previous_value != current_value:
            changes.append(
                {
                    "field": label,
                    "previous": previous_value or "—",
                    "current": current_value or "—",
                }
            )

    return bool(changes), changes


def _apply_match(record, status, matched_entry, match_type):
    new_snapshot = _build_snapshot(status, matched_entry)
    change_detected, changes = _detect_changes(record.current_snapshot, new_snapshot)

    record.status = status
    record.matched_entry = matched_entry
    record.match_type = match_type
    record.change_detected = change_detected
    record.changes = changes
    record.previous_snapshot = record.current_snapshot
    record.current_snapshot = new_snapshot
    record.last_checked = timezone.now()
    return record


def ensure_registry_records_exist():
    """Every real Customer gets exactly one registry record -- backfills
    any customer that existed before the registry did, and any created
    since. Uses the Customer's own primary key (OneToOneField), never a
    name match, so it can never create a duplicate or link the wrong
    customer. Never recomputes an existing record's status -- that only
    ever happens via check_customer() / check_all_customers() below.
    """
    unregistered_ids = list(Customer.objects.filter(registry_record__isnull=True).values_list("id", flat=True))
    for customer_id in unregistered_ids:
        IntermediateRegistryRecord.objects.get_or_create(customer_id=customer_id)


def check_customer(customer):
    """Re-runs the registry match for exactly one customer -- creates its
    record first if this is the very first time it's been checked."""
    matches, match_type = find_registry_matches(customer.carrier)
    status = classify_matches(matches)
    matched_entry = matches[0] if status == "present" else None

    record, _created = IntermediateRegistryRecord.objects.get_or_create(customer=customer)
    _apply_match(record, status, matched_entry, match_type)
    record.save()
    return record


def check_all_customers():
    """Re-runs the registry match for every registered customer in one
    bulk pass (a fixed, small number of queries regardless of how many
    customers there are -- see matching.find_registry_matches_bulk).
    Meant to run right after a fresh CSV import, so every customer's
    status (and change_detected, against whatever the *previous* import
    found) reflects the newest registry data -- see
    management/commands/import_intermediate_registry.py.
    """
    ensure_registry_records_exist()

    records = list(IntermediateRegistryRecord.objects.select_related("customer").all())
    names = [record.customer.carrier for record in records]
    grouped = find_registry_matches_bulk(names)

    for record in records:
        matches, match_type = grouped.get(record.customer.carrier, ([], None))
        status = classify_matches(matches)
        matched_entry = matches[0] if status == "present" else None
        _apply_match(record, status, matched_entry, match_type)

    IntermediateRegistryRecord.objects.bulk_update(
        records,
        ["status", "matched_entry", "match_type", "change_detected", "changes", "previous_snapshot", "current_snapshot", "last_checked"],
    )
    return len(records)


def active_escalation_for(registry_record):
    """The one currently OPEN or IN REVIEW escalation for this registry
    check, if any -- real database records only, never a guess. Used both
    to block creating a duplicate active escalation on the same check and
    to show "Escalation Open" instead of the Escalate button (see
    views.RegistryEscalationCreateView)."""
    return registry_record.escalations.filter(status__in=ACTIVE_ESCALATION_STATUSES).order_by("-created_at").first()
