"""Central FCC-side company lookup, shared by the RMD, FCC, and Customers
modules so they all see the same match result for the same company name.

Matching against the local cache is staged the same way as RMD's (see
verification.rmd_lookup): exact normalized match first, then -- only if that
finds nothing -- a broadened match combining substring search and a
legal-suffix-stripped substring search, so a cached "XYZ Ltd." record is
still found for a customer named "XYZ Limited" and vice versa.

FCC Form 499 data isn't a bulk-imported dataset like RMD though -- it's
fetched on demand -- so if neither cache tier finds anything, this module
falls back (when the caller allows it) to the same adapted FCC lookup
service the FCC Compliance module itself uses (fcc499.lookup). Callers bound
how many live fetches happen per request (DEFAULT_LIVE_FETCH_BUDGET below is
a sane default) so a broad search can't trigger a burst of slow network
scrapes.
"""
from datetime import datetime

from django.db.models import Q

from fcc499 import lookup as fcc_service
from fcc499.models import Fcc499Filing
from rmd.compliance import OPERATIONAL_STATUS_THRESHOLD

from .normalize import contains_as_word, normalize_name, normalized_name_expr, strip_legal_suffix

DEFAULT_LIVE_FETCH_BUDGET = 3

# The FCC's own Form 499 annual re-registration deadline is April 1 --
# registration_current_as_of on a real record is either that year's deadline
# (e.g. "4/1/2026", meaning the filer re-registered for the current cycle) or
# a stale, older date if they haven't. Operational Status for the Customers
# module is driven by this FCC field, not by RMD's own last_recertified.
FCC_DATE_INPUT_FORMATS = ("%m/%d/%Y", "%Y-%m-%d")


def compute_fcc_operational_status(registration_current_as_of):
    """Active/Inactive from the FCC record's registration_current_as_of --
    a free-text field scraped from the FCC site, always M/D/YYYY in
    practice. No usable date on file is treated as Inactive, matching
    rmd.compliance.compute_operational_status's "no evidence it's current"
    stance."""
    value = (registration_current_as_of or "").strip()
    if not value:
        return "inactive"
    for date_format in FCC_DATE_INPUT_FORMATS:
        try:
            parsed = datetime.strptime(value, date_format).date()
            break
        except ValueError:
            continue
    else:
        return "inactive"
    return "active" if parsed >= OPERATIONAL_STATUS_THRESHOLD else "inactive"

_EMPTY_RESULT = {
    "matched_records": [],
    "match_type": None,
    "record_id": None,
    "frn": None,
    "detail_available": False,
}


def _exact_cached_queryset(targets):
    return Fcc499Filing.objects.annotate(
        _norm_legal=normalized_name_expr("legal_name"),
        _norm_dba=normalized_name_expr("doing_business_as"),
    ).filter(Q(_norm_legal__in=targets) | Q(_norm_dba__in=targets))


def _broadened_query_for(company_name, norm, core):
    """A cheap SQL prefilter only -- see contains_as_word() in normalize.py
    for the real word-boundary check applied to whatever this returns."""
    query = Q(legal_name__icontains=company_name.strip()) | Q(doing_business_as__icontains=company_name.strip())
    if core and core != norm:
        query |= Q(legal_name__icontains=core) | Q(doing_business_as__icontains=core)
    return query


def _is_broadened_hit(legal_name, doing_business_as, company_name, norm, core):
    if contains_as_word(legal_name, company_name) or contains_as_word(doing_business_as, company_name):
        return True
    if core and core != norm:
        return contains_as_word(legal_name, core) or contains_as_word(doing_business_as, core)
    return False


def find_cached_matches(company_name):
    """(matches, match_type) for one company name against the local cache."""
    company_name = (company_name or "").strip()
    norm = normalize_name(company_name)
    if not norm:
        return [], None

    exact = list(_exact_cached_queryset({norm}).order_by("legal_name"))
    if exact:
        return exact, "exact_normalized"

    core = strip_legal_suffix(norm)
    prefiltered = Fcc499Filing.objects.filter(_broadened_query_for(company_name, norm, core)).order_by("legal_name")
    broad = [
        r for r in prefiltered if _is_broadened_hit(r.legal_name, r.doing_business_as, company_name, norm, core)
    ]
    return (broad, "broadened") if broad else ([], None)


def find_cached_matches_bulk(company_names):
    """(matches, match_type) for many company names in a fixed, small number
    of queries. Returns {original_name: (matches, match_type)}. Never
    triggers a live fetch -- that only ever happens for a specific,
    individually-requested company (see verification_from_grouped).
    """
    names = [n for n in company_names if (n or "").strip()]
    if not names:
        return {}

    prepared = {name: normalize_name(name) for name in names}
    target_norms = set(prepared.values())

    exact_grouped = {}
    for record in _exact_cached_queryset(target_norms).order_by("legal_name"):
        # A record whose legal_name and doing_business_as normalize the same
        # way (common) must only be added once per matching key.
        matched_keys = {
            key
            for key in (normalize_name(record.legal_name), normalize_name(record.doing_business_as))
            if key in target_norms
        }
        for key in matched_keys:
            exact_grouped.setdefault(key, []).append(record)

    result = {}
    unresolved = [name for name, norm in prepared.items() if norm not in exact_grouped]

    broad_grouped = {}
    if unresolved:
        combined_query = Q()
        for name in unresolved:
            norm = prepared[name]
            core = strip_legal_suffix(norm)
            combined_query |= _broadened_query_for(name, norm, core)

        for record in Fcc499Filing.objects.filter(combined_query).order_by("legal_name"):
            for name in unresolved:
                norm = prepared[name]
                core = strip_legal_suffix(norm)
                if _is_broadened_hit(record.legal_name, record.doing_business_as, name, norm, core):
                    broad_grouped.setdefault(name, []).append(record)

    for name, norm in prepared.items():
        if norm in exact_grouped:
            result[name] = (exact_grouped[norm], "exact_normalized")
        elif name in broad_grouped:
            result[name] = (broad_grouped[name], "broadened")
        else:
            result[name] = ([], None)

    return result


def _serialize(filing):
    return {
        "id": filing.id,
        "filer_id": filing.filer_id,
        "legal_name": filing.legal_name,
        "doing_business_as": filing.doing_business_as,
        "usf_contributor": filing.usf_contributor,
        # cores_id is the FCC Form 499 page's "Registration Number (CORESID)"
        # field -- confirmed against real data to be the same identifier as
        # RMD's FRN (same digit string for the same real company), so it's
        # exposed here as the comparable "frn" value. See verification.frn.
        "cores_id": filing.cores_id,
        "frn": filing.cores_id,
        "registration_current_as_of": filing.registration_current_as_of,
        "operational_status": compute_fcc_operational_status(filing.registration_current_as_of),
        "detail_url": filing.detail_url,
    }


def _wrap(matches, match_type):
    if not matches:
        status = "not_present"
    elif len(matches) == 1:
        status = "present"
    else:
        status = "multiple_matches"

    matched_records = [_serialize(m) for m in matches]

    return {
        "status": status,
        "matched_records": matched_records,
        "match_type": match_type if matches else None,
        "record_id": matched_records[0]["id"] if len(matched_records) == 1 else None,
        "frn": matched_records[0]["frn"] if len(matched_records) == 1 else None,
        "detail_available": bool(matched_records),
    }


def _live_search(company_name):
    """Best-effort: run the real FCC Form 499 site search for company_name
    (see fcc499.lookup.search) and cache *every* filer it returns -- not
    just a single exact-name fetch. A carrier can genuinely match more than
    one real FCC filer (e.g. "Bharti Airtel" -> 2, and some names resolve to
    far more), so a single fetch_and_cache() call would silently stop at the
    first one. This lets find_cached_matches() see the complete result set
    afterward. Never raises -- fcc499.lookup.search already swallows
    network/parse failures internally and falls back to whatever's cached."""
    company_name = (company_name or "").strip()
    if company_name:
        fcc_service.search(company_name)


def _refresh_via_live_search(company_name):
    """Real, complete live FCC search (bounded by the caller) for
    company_name, after which find_cached_matches() sees every filer the
    live site actually returned -- or an honest "not_present" if it truly
    found nothing."""
    _live_search(company_name)
    matches, match_type = find_cached_matches(company_name)
    if matches:
        return _wrap(matches, match_type)
    return {"status": "not_present", **_EMPTY_RESULT}


def verification_from_name(company_name, allow_live_fetch):
    """The fcc_verification block for an arbitrary company name.

    allow_live_fetch controls whether this name may trigger a real, live FCC
    search (bounded by the caller). A cached match that isn't already an
    exact normalized match is only a partial signal -- the real FCC database
    can hold more matching filers than whatever's happened to be cached
    before -- so whenever live lookups are allowed and the cache doesn't
    already have a confirmed exact match, this re-checks the live FCC search
    results page first so the *complete* set of real matches is found (see
    _live_search). When allow_live_fetch is False and nothing is cached, the
    result is "verification_pending" rather than a guess.
    """
    matches, match_type = find_cached_matches(company_name)
    if matches and match_type == "exact_normalized":
        return _wrap(matches, match_type)

    if allow_live_fetch:
        return _refresh_via_live_search(company_name)

    if matches:
        return _wrap(matches, match_type)
    return {"status": "verification_pending", **_EMPTY_RESULT}


def verification_from_grouped(company_name, grouped, allow_live_fetch):
    """The fcc_verification block using a pre-fetched find_cached_matches_bulk()
    result -- no additional query unless this specific name isn't already an
    exact cached match and allow_live_fetch is True (bounded by the caller,
    e.g. only for the first few rows on a page), in which case it's re-checked
    against a real live FCC search the same way verification_from_name does."""
    matches, match_type = grouped.get(company_name, ([], None))
    if matches and match_type == "exact_normalized":
        return _wrap(matches, match_type)

    if not allow_live_fetch:
        if matches:
            return _wrap(matches, match_type)
        return {"status": "verification_pending", **_EMPTY_RESULT}

    return _refresh_via_live_search(company_name)


def verification_from_record(record):
    """The fcc_verification block for an Fcc499Filing the caller already has
    (used by the FCC Compliance module itself -- no need to re-search)."""
    return _wrap([record] if record else [], "exact_normalized" if record else None)
