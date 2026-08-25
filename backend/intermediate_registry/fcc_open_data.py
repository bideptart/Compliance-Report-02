"""Live source for the Intermediate Provider Registry data -- the FCC's
own official open data portal, not a locally-uploaded CSV.

https://opendata.fcc.gov/dataset/Intermediate-Provider-Registry/a6ec-cry4

This is a Socrata (SODA) API: a plain paginated JSON endpoint, no API key
required for a dataset this size. Field names on the live API already
match this app's own model field names exactly (business_name,
business_address, regulatory_contact_name/title/telephone/email) -- no
column-name translation needed, unlike the old CSV import which had to map
"Business Name" (title case, spaces) to business_name.
"""
import requests

DATASET_RESOURCE_URL = "https://opendata.fcc.gov/resource/a6ec-cry4.json"

# Only these fields are ever used -- every other field the API returns
# (previous_business_names, states_serviced, regulatory_contact_address,
# every rural_call_completion_contact_* field) is intentionally ignored,
# same scope as the CSV import this replaces.
FIELDS = (
    "business_name",
    "business_address",
    "regulatory_contact_name",
    "regulatory_contact_title",
    "regulatory_contact_telephone",
    "regulatory_contact_email",
)

REQUEST_TIMEOUT = 30
PAGE_SIZE = 1000


class RegistryFetchError(Exception):
    """Raised when the live FCC open data API can't be reached or
    returns something unusable."""


def fetch_registry_rows():
    """Every real row currently in the FCC's Intermediate Provider
    Registry dataset -- paginated via $limit/$offset so this stays
    correct even if the dataset grows past one page. Never raises for an
    individual bad row; only raises RegistryFetchError if the live source
    itself can't be reached at all (the caller can then decide whether to
    keep whatever was previously imported rather than wipe it out).
    """
    rows = []
    offset = 0

    while True:
        try:
            response = requests.get(
                DATASET_RESOURCE_URL,
                params={"$limit": PAGE_SIZE, "$offset": offset, "$select": ",".join(FIELDS)},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            page = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise RegistryFetchError(f"Could not fetch the Intermediate Provider Registry: {exc}") from exc

        if not isinstance(page, list):
            raise RegistryFetchError("Unexpected response shape from the Intermediate Provider Registry API.")

        rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    return rows
