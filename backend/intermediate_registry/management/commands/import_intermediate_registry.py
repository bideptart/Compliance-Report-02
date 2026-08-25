import math

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from intermediate_registry.fcc_open_data import RegistryFetchError, fetch_registry_rows
from intermediate_registry.models import IntermediateRegistryEntry
from intermediate_registry.services import check_all_customers


def clean_value(value):
    """Normalize a raw API value into either a clean string or None."""
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    text = str(value).strip()
    if text == "" or text.lower() in ("nan", "none", "null", "n/a"):
        return None
    return text


class Command(BaseCommand):
    help = (
        "Import the Intermediate Provider Registry as a lookup table, live "
        "from the FCC's own official open data portal (Business Name, "
        "Business Address, Regulatory Contact Name/Title/Telephone/Email "
        "only -- every other field is ignored), then re-check every real "
        "Customer's Present/Not Present/Review Required status against the "
        "freshly-imported data."
    )

    def handle(self, *args, **options):
        try:
            rows = fetch_registry_rows()
        except RegistryFetchError as exc:
            raise CommandError(str(exc))

        total = imported = skipped = 0
        entries = []
        for row in rows:
            total += 1
            business_name = clean_value(row.get("business_name"))
            if not business_name:
                skipped += 1
                continue

            entries.append(
                IntermediateRegistryEntry(
                    business_name=business_name,
                    business_address=clean_value(row.get("business_address")),
                    regulatory_contact_name=clean_value(row.get("regulatory_contact_name")),
                    regulatory_contact_title=clean_value(row.get("regulatory_contact_title")),
                    regulatory_contact_telephone=clean_value(row.get("regulatory_contact_telephone")),
                    regulatory_contact_email=clean_value(row.get("regulatory_contact_email")),
                )
            )

        # A fresh import always fully replaces the prior one -- this is
        # reference/lookup data (like RMD/FCC), not something a person
        # edits row-by-row, so there's no "existing entry" to merge with.
        # Every real Customer's matched_entry FK is SET_NULL, so clearing
        # this table can never leave a dangling reference.
        with transaction.atomic():
            IntermediateRegistryEntry.objects.all().delete()
            IntermediateRegistryEntry.objects.bulk_create(entries)
            imported = len(entries)

        checked = check_all_customers()

        self.stdout.write(self.style.SUCCESS("Intermediate Provider Registry import complete"))
        self.stdout.write("  Source                     : FCC Open Data (opendata.fcc.gov, dataset a6ec-cry4)")
        self.stdout.write(f"  Rows fetched               : {total}")
        self.stdout.write(f"  Registry entries imported  : {imported}")
        self.stdout.write(f"  Skipped (no Business Name) : {skipped}")
        self.stdout.write(f"  Customers re-checked       : {checked}")
