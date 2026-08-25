import csv
import math
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from customers.models import Customer, normalize_carrier

# Some source rows carry a leftover "Name" label from the original export
# template (e.g. "Name QGCommunications", "NAME CMI", "Name- execall") --
# not part of the real carrier name, so it's stripped before storing.
NAME_PREFIX_RE = re.compile(r"^name[\s-]*", re.IGNORECASE)

# A per-country traffic report's "Vendor" column carries a "this row is a
# vendor" label baked into the value itself (e.g. "Apelby GmbH (Vendor)",
# "925 Telecom vendor", "LAST MILE CORP - VENDOR") -- never part of the
# company's own legal name. Left in place, it breaks every RMD/FCC
# name-based match for that company (the real RMD filing is just "Apelby
# GmbH"), so it's stripped the same way NAME_PREFIX_RE strips the "Name"
# label above. Deliberately singular-only ("Vendor", not "Vendors") and
# anchored to the very end of the string, so a genuine company name that
# happens to end in "Vendors" (plural) -- e.g. a literal "Rural Vendors" --
# is never touched, only this exact known label pattern is.
TRAILING_VENDOR_LABEL_RE = re.compile(r"[\s\-]*\(?\s*vendor\)?\s*$", re.IGNORECASE)


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


def clean_carrier_name(value):
    """Strip the stray leading 'Name' label and trailing 'Vendor' report
    label, and collapse internal whitespace."""
    value = NAME_PREFIX_RE.sub("", value).strip()
    value = TRAILING_VENDOR_LABEL_RE.sub("", value).strip()
    value = re.sub(r"\s+", " ", value)
    return value or None


# Real export formats seen so far use either header for the same thing --
# a company's own name is the only column ever imported, regardless of
# which label the source file uses. Checked in this order.
CARRIER_COLUMN_CANDIDATES = ["Carrier", "Vendor"]

# A trailing spreadsheet summary row (e.g. "Total" with aggregate figures in
# the other columns) is not a real company -- skipped by name, case
# insensitively, never imported as a carrier.
_NON_CARRIER_VALUES = {"total"}


class Command(BaseCommand):
    help = (
        "Import unique carrier/vendor names from a real export CSV. Only the "
        "name column itself is used (Carrier or Vendor, whichever the file "
        "has) -- every other column (Country, Provider, traffic stats, "
        "revenue, ...) is ignored."
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to the customer CSV file")

    def handle(self, *args, **options):
        csv_path = options["csv_path"]

        try:
            csv_file = open(csv_path, encoding="utf-8-sig", newline="")
        except OSError as exc:
            raise CommandError(f"Could not open CSV file at '{csv_path}': {exc}")

        total = skipped = failed = 0
        # carrier_key -> (carrier, is_usa_row) -- the same real company can
        # appear once per country in a per-country traffic report (e.g. one
        # row for USA, one for Canada). Only one Customer is ever created per
        # company, and when it has a USA row that one always wins over a
        # non-USA row for the same company; a company with no USA row at all
        # still imports fine, from whichever row it does have.
        chosen_rows = {}

        with csv_file:
            reader = csv.DictReader(csv_file)

            fieldnames = reader.fieldnames or []
            carrier_column = next((c for c in CARRIER_COLUMN_CANDIDATES if c in fieldnames), None)
            if carrier_column is None:
                raise CommandError(
                    "CSV is missing a name column -- expected one of: " + ", ".join(CARRIER_COLUMN_CANDIDATES)
                )
            has_country_column = "Country" in fieldnames

            for row in reader:
                total += 1
                carrier = clean_value(row.get(carrier_column))
                if carrier:
                    carrier = clean_carrier_name(carrier)

                if not carrier:
                    skipped += 1
                    self.stderr.write(f"Row {total}: skipped, missing '{carrier_column}' value")
                    continue

                if carrier.strip().lower() in _NON_CARRIER_VALUES:
                    skipped += 1
                    self.stderr.write(f"Row {total}: skipped, '{carrier}' is a summary row, not a real carrier")
                    continue

                carrier_key = normalize_carrier(carrier)
                is_usa_row = has_country_column and (clean_value(row.get("Country")) or "").strip().upper() == "USA"

                existing = chosen_rows.get(carrier_key)
                if existing is None or (is_usa_row and not existing[1]):
                    chosen_rows[carrier_key] = (carrier, is_usa_row)

        imported = updated = 0
        with transaction.atomic():
            for carrier_key, (carrier, _is_usa_row) in chosen_rows.items():
                try:
                    with transaction.atomic():
                        obj, created = Customer.objects.update_or_create(
                            carrier_key=carrier_key, defaults={"carrier": carrier}
                        )
                except Exception as exc:
                    failed += 1
                    self.stderr.write(f"{carrier}: failed - {exc}")
                    continue

                if created:
                    imported += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS("Customer import complete"))
        self.stdout.write(f"  Total rows read      : {total}")
        self.stdout.write(f"  Unique carriers new  : {imported}")
        self.stdout.write(f"  Unique carriers seen : {updated}")
        self.stdout.write(f"  Skipped              : {skipped}")
        self.stdout.write(f"  Failed               : {failed}")
