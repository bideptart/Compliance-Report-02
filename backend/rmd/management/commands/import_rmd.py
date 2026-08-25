import csv
import math
import re
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from rmd.models import RmdFiling

SYS_ID_PATTERN = re.compile(r"[?&]sys_id=([0-9a-fA-F]+)")

# CSV columns that map 1:1 onto model fields as plain text.
TEXT_FIELDS = [
    "frn",
    "business_name",
    "business_address",
    "foreign_voice_provider",
    "country",
    "other_frns",
    "other_dba_names",
    "previous_dba_names",
    "robocall_mitigation_contact_name",
    "contact_title",
    "contact_department",
    "contact_business_address",
    "contact_country",
    "contact_telephone_number",
    "contact_phone_extension",
    "implementation",
    "voice_service_provider_choice",
    "gateway_provider_choice",
    "intermediate_provider_choice",
]

DATE_FIELDS = ["last_updated", "last_recertified"]


def clean_value(value):
    """Normalize a raw CSV cell into either a clean string or None."""
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    text = str(value).strip()
    if text == "" or text.lower() in ("nan", "none", "null", "n/a", "inf", "-inf", "infinity", "-infinity"):
        return None
    return text


DATE_INPUT_FORMATS = (
    "%Y-%m-%d",  # ISO -- the format actually used by the RMD CSV export.
    "%m/%d/%Y",  # MM/DD/YYYY -- explicit, never DD/MM/YYYY, for any
    # slash-formatted date this or a future RMD export might contain.
)


def parse_date(value):
    value = clean_value(value)
    if value is None:
        return None
    for date_format in DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    return None


def extract_sys_id(filing_url):
    if not filing_url:
        return None
    match = SYS_ID_PATTERN.search(filing_url)
    return match.group(1) if match else None


class Command(BaseCommand):
    help = "Import Robocall Mitigation Database (RMD) records from the official FCC CSV export."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to the RMD CSV file")

    def handle(self, *args, **options):
        csv_path = options["csv_path"]

        try:
            csv_file = open(csv_path, encoding="utf-8-sig", newline="")
        except OSError as exc:
            raise CommandError(f"Could not open CSV file at '{csv_path}': {exc}")

        total = imported = updated = skipped = failed = 0

        with csv_file, transaction.atomic():
            reader = csv.DictReader(csv_file)

            missing_columns = {"number", "filing_url"} - set(reader.fieldnames or [])
            if missing_columns:
                raise CommandError(
                    f"CSV is missing required column(s): {', '.join(sorted(missing_columns))}"
                )

            for row in reader:
                total += 1
                number = clean_value(row.get("number"))

                if not number:
                    skipped += 1
                    self.stderr.write(f"Row {total}: skipped, missing 'number' identifier")
                    continue

                filing_url = clean_value(row.get("filing_url"))
                sys_id = extract_sys_id(filing_url)

                fields = {"number": number, "sys_id": sys_id, "filing_url": filing_url}
                for field in TEXT_FIELDS:
                    fields[field] = clean_value(row.get(field))
                for field in DATE_FIELDS:
                    fields[field] = parse_date(row.get(field))

                try:
                    with transaction.atomic():
                        lookup = {"sys_id": sys_id} if sys_id else {"number": number}
                        obj, created = RmdFiling.objects.update_or_create(
                            **lookup, defaults=fields
                        )
                except Exception as exc:
                    failed += 1
                    self.stderr.write(f"Row {total} ({number}): failed - {exc}")
                    continue

                if created:
                    imported += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS("RMD import complete"))
        self.stdout.write(f"  Total rows read : {total}")
        self.stdout.write(f"  Imported (new)  : {imported}")
        self.stdout.write(f"  Updated         : {updated}")
        self.stdout.write(f"  Skipped         : {skipped}")
        self.stdout.write(f"  Failed          : {failed}")
