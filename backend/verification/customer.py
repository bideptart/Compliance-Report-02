"""Full Carrier -> RMD + FCC + FRN verification, used by the Customers module.

Thin composition of the other verification.* modules -- keeps Customers from
having its own copy of the matching/comparison logic.
"""
import re

from intermediate_registry.models import IntermediateRegistryRecord
from intermediate_registry.models import STATUS_CHOICES as REGISTRY_STATUS_CHOICES

from . import fcc_lookup, frn, rmd_lookup

# Real-world country strings that all mean "domestic" for the Foreign Voice
# Provider filter -- normalized (trimmed, lowercased) before comparison.
_USA_ALIASES = {"usa", "us", "u.s.", "u.s.a.", "united states", "united states of america"}

# Reuses the Intermediate Registry app's own status codes/labels as the one
# source of truth for what "present" means there -- never a second,
# possibly-drifting copy of that vocabulary.
_REGISTRY_STATUS_LABELS = dict(REGISTRY_STATUS_CHOICES)
_REGISTRY_NOT_CHECKED_STATUS = "not_present"

COMPLIANCE_STATUS_CHOICES = (
    "all",
    "fully_compliant",
    "rmd_not_satisfied",
    "no_filer_id",
    "not_active",
    "foreign_voice_provider",
    "no_intermediate_registry",
)


def _intermediate_registry_status(customer):
    """This customer's real Intermediate Registry status (see
    intermediate_registry.matching) -- never a live re-check here, just a
    read of whatever the registry's own last check already computed.
    Defaults to "not_present" (never "fully compliant") when the customer
    has no registry record yet, e.g. the registry hasn't been checked
    since this customer was added."""
    record = getattr(customer, "registry_record", None)
    return record.status if record is not None else _REGISTRY_NOT_CHECKED_STATUS


def _intermediate_registry_statuses_bulk(customers):
    """{customer_id: status} for many customers in one query -- mirrors
    the same bulk-not-N+1 approach as rmd_lookup/fcc_lookup's *_bulk
    functions. Missing customers default to "not_present", same as the
    single-customer path above."""
    customer_ids = [c.id for c in customers]
    return dict(
        IntermediateRegistryRecord.objects.filter(customer_id__in=customer_ids).values_list("customer_id", "status")
    )


def _company_name(customer, rmd_verification, fcc_verification):
    if rmd_verification["status"] == "present":
        name = rmd_verification["matched_records"][0].get("business_name")
        if name:
            return name
    if fcc_verification["status"] == "present":
        name = fcc_verification["matched_records"][0].get("legal_name")
        if name:
            return name
    return customer.carrier


def _country(rmd_verification):
    # Country isn't stored on Customer (removed by design -- see the
    # Customers module's own model). The only real, non-invented source for
    # it is the matched RMD record's own country field.
    if rmd_verification["status"] != "present":
        return None
    return rmd_verification["matched_records"][0].get("country_of_origin")


def _operational_status(fcc_verification):
    # Active/Inactive is determined from the FCC Form 499 record's own
    # annual re-registration date, not RMD's last_recertified -- see
    # verification.fcc_lookup.compute_fcc_operational_status.
    if fcc_verification["status"] != "present":
        return None
    return fcc_verification["matched_records"][0].get("operational_status")


def _filer_id(fcc_verification):
    if fcc_verification["status"] != "present":
        return None
    return fcc_verification["matched_records"][0].get("filer_id")


def _normalize_country(value):
    if not value:
        return None
    return re.sub(r"\s+", " ", value.strip().lower())


def _disambiguate_rmd_by_frn(rmd_verification, fcc_verification):
    """When RMD matching found multiple candidates AND the FCC side is
    itself a single, confirmed match, try to narrow the RMD candidates down
    to the one real company using that confirmed FCC FRN -- e.g. "BHARTI
    AIRTEL" can match three RMD filings (US/India/UK entities), but if
    exactly one of them shares its FRN with a single confirmed FCC record,
    that one is the actual match.

    Deliberately does NOT attempt this when the FCC side is *itself*
    ambiguous (status == "multiple_matches", e.g. two real FCC filings for
    the same company): picking a "winner" there would silently hide the
    other real FCC candidates from the UI. When FCC is ambiguous too, RMD is
    left as multiple_matches so both sides show every real candidate --
    the central FRN check (verification.frn.verify_frn_match) already
    cross-references every candidate on both sides regardless, so the FRN
    Match verdict is still accurate even without picking a single "winner"
    record on either side.
    """
    if rmd_verification["status"] != "multiple_matches":
        return rmd_verification
    if fcc_verification["status"] != "present":
        return rmd_verification

    fcc_frn = (fcc_verification["matched_records"][0].get("frn") or "").strip()
    if not fcc_frn:
        return rmd_verification

    resolved = [m for m in rmd_verification["matched_records"] if (m.get("frn") or "").strip() == fcc_frn]
    if len(resolved) != 1:
        return rmd_verification

    match = resolved[0]
    return {
        "status": "present",
        "matched_records": [match],
        "match_type": "frn_disambiguated",
        "record_id": match["id"],
        "frn": match["frn"],
        "detail_available": True,
    }


def _compute_compliance(result):
    """The dropdown-filter conditions, computed from real verified fields
    only -- never guessed when a required condition is missing or the
    company match itself is uncertain."""
    rmd_status = result["rmd_verification"]["status"]
    fcc_status = result["fcc_verification"]["status"]
    frn_status = result["frn_verification"]["status"]
    registry_status = result["intermediate_registry_status"]

    fully_compliant = bool(
        result["company_name"]
        and result["country"]
        and rmd_status == "present"
        and result["operational_status"] == "active"
        and frn_status == "matched"
        and registry_status == "present"
    )

    # True whenever the customer is not a confirmed Present match in the
    # Intermediate Registry -- covers both a real "not_present" and an
    # unresolved "review_required", since neither is a pass (see
    # intermediate_registry.matching.classify_matches).
    no_intermediate_registry = registry_status != "present"

    # Explicitly "not_present" only -- a company matching more than one RMD
    # record (rmd_status == "multiple_matches") genuinely IS in RMD, just
    # not yet resolved to one specific filing (see _disambiguate_rmd_by_frn),
    # so it's not counted as "not satisfied" either -- it's surfaced to the
    # UI as a real, honest ambiguity instead.
    rmd_not_satisfied = rmd_status == "not_present"

    # True whenever there is no confirmed Filer ID on file for this company --
    # whether that's because no FCC record was found at all, the match is
    # still unresolved, or an FCC record exists with a blank Filer ID.
    filer_id = result["filer_id"]
    no_filer_id = not (filer_id or "").strip()

    # Operational Status itself comes from the FCC record (see
    # _operational_status), so "not active" is about the FCC match, not RMD.
    not_active = fcc_status == "present" and result["operational_status"] == "inactive"

    normalized_country = _normalize_country(result["country"])
    foreign_voice_provider = bool(result["country"]) and normalized_country not in _USA_ALIASES

    return {
        "fully_compliant": fully_compliant,
        "rmd_not_satisfied": rmd_not_satisfied,
        "no_filer_id": no_filer_id,
        "not_active": not_active,
        "foreign_voice_provider": foreign_voice_provider,
        "no_intermediate_registry": no_intermediate_registry,
    }


def build_result(customer, rmd_verification, fcc_verification, intermediate_registry_status=None):
    """Assemble the final per-customer verification payload from already-
    computed rmd_verification/fcc_verification blocks -- used both for a
    single on-demand lookup and for a batch of pre-fetched (bulk) results.

    intermediate_registry_status: the customer's real Present/Not Present/
    Review Required status from the Intermediate Registry (see
    intermediate_registry.matching) -- passed in by the caller (already
    fetched, single or bulk) rather than queried again here, so this stays
    a pure "given these building blocks, compute the result" function.
    """
    rmd_verification = _disambiguate_rmd_by_frn(rmd_verification, fcc_verification)
    frn_verification = frn.verify_frn_match(rmd_verification, fcc_verification)

    if intermediate_registry_status is None:
        intermediate_registry_status = _intermediate_registry_status(customer)

    result = {
        "id": customer.id,
        "carrier": customer.carrier,
        "company_name": _company_name(customer, rmd_verification, fcc_verification),
        "country": _country(rmd_verification),
        "operational_status": _operational_status(fcc_verification),
        "filer_id": _filer_id(fcc_verification),
        "rmd_verification": rmd_verification,
        "fcc_verification": fcc_verification,
        "frn_verification": frn_verification,
        "intermediate_registry_status": intermediate_registry_status,
        "intermediate_registry_status_label": _REGISTRY_STATUS_LABELS.get(
            intermediate_registry_status, intermediate_registry_status
        ),
    }
    result["compliance"] = _compute_compliance(result)
    return result


def get_customer_verification(customer, allow_live_fcc_fetch, rmd_record=None, fcc_record=None):
    """Single-customer verification (one RMD query + one FCC cache query,
    plus an optional live FCC fetch). For a whole page of customers, use
    get_customer_verifications_bulk instead to avoid N+1 queries.

    rmd_record / fcc_record: when the carrier's name-based match is
    ambiguous (multiple real RMD and/or FCC candidates -- e.g. "BHARTI
    AIRTEL"), the UI lets a person pick which real record is actually this
    customer. Passing the chosen RmdFiling/Fcc499Filing object here pins
    that side to exactly that record ("present", not "multiple_matches"),
    so company name, country, operational status, filer ID, and compliance
    are all recomputed from the confirmed choice instead of staying
    unresolved. Picking only one side leaves the other exactly as its own
    name-based match already resolved it -- still ambiguous if it genuinely
    is, never guessed.

    When neither is passed, this falls back to the customer's own saved
    ``linked_rmd_record`` / ``linked_fcc_record`` (see customers.models.
    Customer and CustomerLinkRecordsView) -- a previously confirmed choice
    stays resolved on every future call, not just for the request that made
    it. An explicit rmd_record/fcc_record argument (e.g. a candidate the UI
    is previewing before it's saved) always takes precedence over the saved
    link.
    """
    rmd_record = rmd_record or customer.linked_rmd_record
    fcc_record = fcc_record or customer.linked_fcc_record

    rmd_verification = (
        rmd_lookup.verification_from_record(rmd_record) if rmd_record else rmd_lookup.verification_from_name(customer.carrier)
    )
    fcc_verification = (
        fcc_lookup.verification_from_record(fcc_record)
        if fcc_record
        else fcc_lookup.verification_from_name(customer.carrier, allow_live_fcc_fetch)
    )
    return build_result(customer, rmd_verification, fcc_verification)


def get_customer_verifications_bulk(customers, max_live_fcc_fetches=0):
    """Verification for many customers with a fixed, small number of queries:
    one RMD query and one FCC cache query for the whole batch, regardless of
    how many customers are in it. At most max_live_fcc_fetches customers
    whose FCC status isn't cached may trigger a real (bounded) live lookup;
    the rest are reported as "verification_pending" rather than guessed.

    A customer with a saved linked_rmd_record/linked_fcc_record (see
    get_customer_verification) skips the name-based bulk match on that side
    entirely and is verified straight from the confirmed record instead --
    the same resolution a person made once on the Customer Detail page
    applies here too, so a resolved carrier never goes back to showing
    "Multiple Matches" in a list/search result. Callers should
    select_related("linked_rmd_record", "linked_fcc_record") on the
    queryset they pass in to avoid an N+1 here.
    """
    customers = list(customers)
    names = [c.carrier for c in customers]

    rmd_grouped = rmd_lookup.find_rmd_matches_bulk(names)
    fcc_grouped = fcc_lookup.find_cached_matches_bulk(names)
    registry_statuses = _intermediate_registry_statuses_bulk(customers)

    results = []
    live_fetches_used = 0
    for customer in customers:
        if customer.linked_rmd_record_id:
            rmd_verification = rmd_lookup.verification_from_record(customer.linked_rmd_record)
        else:
            rmd_verification = rmd_lookup.verification_from_grouped(customer.carrier, rmd_grouped)

        if customer.linked_fcc_record_id:
            fcc_verification = fcc_lookup.verification_from_record(customer.linked_fcc_record)
        else:
            allow_live_fetch = live_fetches_used < max_live_fcc_fetches
            is_cached = bool(fcc_grouped.get(customer.carrier, ([], None))[0])
            fcc_verification = fcc_lookup.verification_from_grouped(
                customer.carrier, fcc_grouped, allow_live_fetch=allow_live_fetch
            )
            if not is_cached and allow_live_fetch:
                live_fetches_used += 1

        registry_status = registry_statuses.get(customer.id, _REGISTRY_NOT_CHECKED_STATUS)
        results.append(build_result(customer, rmd_verification, fcc_verification, registry_status))

    return results
