"""Central RMD-side company lookup, shared by the RMD, FCC, and Customers
modules so they all see the same match result for the same company name.

Matching is staged, escalating only when the stricter stage finds nothing --
this is what mirrors the RMD module's own search behavior (which itself uses
a plain substring search) instead of contradicting it:

  Stage 1 -- exact match: case/whitespace-normalized equality against
             business_name. Highest confidence.

  Stage 2 -- broadened match (only tried if Stage 1 finds nothing): the
             union of
               (a) business_name contains the normalized company name, and
               (b) business_name contains the company name with a trailing
                   legal-entity suffix (Ltd/Limited/LLC/Inc/Corp/...)
                   stripped off -- so "XYZ Limited" still finds an RMD
                   record filed as "XYZ Ltd." and vice versa.

Multiple candidates at either stage are never collapsed into a guess: the
caller (verification.customer) may disambiguate a multi-candidate result
using a confirmed FRN from the FCC side; failing that it comes back as
"multiple_matches" (Review Required), never "present" with an arbitrarily
chosen record, and never "not_present" -- that status is reserved for when
no stage finds anything at all.
"""
from django.db.models import Q

from rmd.compliance import compute_operational_status
from rmd.models import RmdFiling

from .normalize import contains_as_word, normalize_name, normalized_name_expr, strip_legal_suffix


def _exact_matches_queryset(targets):
    return RmdFiling.objects.annotate(_norm_name=normalized_name_expr("business_name")).filter(
        _norm_name__in=targets
    )


def _broadened_query_for(company_name, norm, core):
    """A cheap SQL prefilter only -- SQL LIKE has no concept of word
    boundaries, so this can (and does) over-match, e.g. "WIC" against
    "Twiching". contains_as_word() does the real check afterward."""
    query = Q(business_name__icontains=company_name.strip())
    if core and core != norm:
        query |= Q(business_name__icontains=core)
    return query


def _is_broadened_hit(business_name, company_name, norm, core):
    if contains_as_word(business_name, company_name):
        return True
    return bool(core) and core != norm and contains_as_word(business_name, core)


def find_rmd_matches(company_name):
    """(matches, match_type) for one company name."""
    company_name = (company_name or "").strip()
    norm = normalize_name(company_name)
    if not norm:
        return [], None

    exact = list(_exact_matches_queryset({norm}).order_by("business_name"))
    if exact:
        return exact, "exact_normalized"

    core = strip_legal_suffix(norm)
    prefiltered = RmdFiling.objects.filter(_broadened_query_for(company_name, norm, core)).order_by("business_name")
    broad = [r for r in prefiltered if _is_broadened_hit(r.business_name, company_name, norm, core)]
    return (broad, "broadened") if broad else ([], None)


def find_rmd_matches_bulk(company_names):
    """(matches, match_type) for many company names in a fixed, small number
    of queries -- one exact-tier query for the whole batch, plus (only if
    needed) one combined broadened query for whichever names had no exact
    match. Returns {original_name: (matches, match_type)}.
    """
    names = [n for n in company_names if (n or "").strip()]
    if not names:
        return {}

    prepared = {name: normalize_name(name) for name in names}

    exact_grouped = {}
    for record in _exact_matches_queryset(set(prepared.values())).order_by("business_name"):
        exact_grouped.setdefault(normalize_name(record.business_name), []).append(record)

    result = {}
    unresolved = [name for name, norm in prepared.items() if norm not in exact_grouped]

    broad_grouped = {}
    if unresolved:
        combined_query = Q()
        for name in unresolved:
            norm = prepared[name]
            core = strip_legal_suffix(norm)
            combined_query |= _broadened_query_for(name, norm, core)

        for record in RmdFiling.objects.filter(combined_query).order_by("business_name"):
            for name in unresolved:
                norm = prepared[name]
                core = strip_legal_suffix(norm)
                if _is_broadened_hit(record.business_name, name, norm, core):
                    broad_grouped.setdefault(name, []).append(record)

    for name, norm in prepared.items():
        if norm in exact_grouped:
            result[name] = (exact_grouped[norm], "exact_normalized")
        elif name in broad_grouped:
            result[name] = (broad_grouped[name], "broadened")
        else:
            result[name] = ([], None)

    return result


def _serialize(record):
    return {
        "id": record.id,
        "number": record.number,
        "business_name": record.business_name,
        "country_of_origin": record.country,
        "frn": record.frn,
        "operational_status": compute_operational_status(record.last_recertified),
        "filing_url": record.filing_url,
    }


def wrap(matches, match_type):
    """Build the rmd_verification block from an already-resolved candidate
    list. Exposed (not prefixed with _) so verification.customer can call it
    again after FRN-based disambiguation narrows a multi-candidate result.
    """
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


def verification_from_name(company_name):
    """The rmd_verification block for an arbitrary company name (used by the
    FCC and Customers modules, which start without an RMD record in hand)."""
    matches, match_type = find_rmd_matches(company_name)
    return wrap(matches, match_type)


def verification_from_grouped(company_name, grouped):
    """The rmd_verification block using a pre-fetched find_rmd_matches_bulk()
    result -- no additional query."""
    matches, match_type = grouped.get(company_name, ([], None))
    return wrap(matches, match_type)


def verification_from_record(record):
    """The rmd_verification block for an RMD record the caller already has
    (used by the RMD module itself -- no need to re-search)."""
    return wrap([record] if record else [], "exact_normalized" if record else None)
