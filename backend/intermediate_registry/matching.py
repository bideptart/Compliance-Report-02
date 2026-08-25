"""Company-name matching against the imported Intermediate Provider
Registry CSV (see IntermediateRegistryEntry).

Deliberately mirrors the same staged, safe matching approach already used
for RMD (verification.rmd_lookup) and FCC (verification.fcc_lookup) --
reuses their generic, app-agnostic normalization helpers (case/whitespace
normalization, legal-suffix stripping, word-boundary containment) but never
touches RMD/FCC/FRN matching itself, since this is a wholly separate lookup
against a wholly separate dataset.

  Stage 1 -- exact match: case/whitespace-normalized equality against
             business_name. Highest confidence.

  Stage 2 -- broadened match (only tried if Stage 1 finds nothing): the
             union of (a) business_name contains the normalized company
             name as a whole word/phrase, and (b) business_name contains
             the company name with a trailing legal-entity suffix
             stripped off.

Multiple candidates at either stage are never collapsed into a guess --
the caller reports "review_required" (see models.STATUS_CHOICES), never
"present" with an arbitrarily chosen entry. No fuzzy (edit-distance/
similarity-score) matching is used at all -- only these word-boundary-safe
tiers, per the explicit "do not treat a weak partial match as correct"
requirement this module was built against.
"""
from django.db.models import Q

from verification.normalize import contains_as_word, normalize_name, normalized_name_expr, strip_legal_suffix

from .models import IntermediateRegistryEntry


def _exact_matches_queryset(targets):
    return IntermediateRegistryEntry.objects.annotate(_norm_name=normalized_name_expr("business_name")).filter(
        _norm_name__in=targets
    )


def _broadened_query_for(company_name, norm, core):
    query = Q(business_name__icontains=company_name.strip())
    if core and core != norm:
        query |= Q(business_name__icontains=core)
    return query


def _is_broadened_hit(business_name, company_name, norm, core):
    if contains_as_word(business_name, company_name):
        return True
    return bool(core) and core != norm and contains_as_word(business_name, core)


def find_registry_matches(company_name):
    """(matches, match_type) for one company/carrier name."""
    company_name = (company_name or "").strip()
    norm = normalize_name(company_name)
    if not norm:
        return [], None

    exact = list(_exact_matches_queryset({norm}).order_by("business_name"))
    if exact:
        return exact, "exact_normalized"

    core = strip_legal_suffix(norm)
    prefiltered = IntermediateRegistryEntry.objects.filter(
        _broadened_query_for(company_name, norm, core)
    ).order_by("business_name")
    broad = [e for e in prefiltered if _is_broadened_hit(e.business_name, company_name, norm, core)]
    return (broad, "broadened") if broad else ([], None)


def find_registry_matches_bulk(company_names):
    """(matches, match_type) for many names in a fixed, small number of
    queries -- one exact-tier query for the whole batch, plus (only if
    needed) one combined broadened query for whichever names had no exact
    match. Returns {original_name: (matches, match_type)}.
    """
    names = [n for n in company_names if (n or "").strip()]
    if not names:
        return {}

    prepared = {name: normalize_name(name) for name in names}

    exact_grouped = {}
    for entry in _exact_matches_queryset(set(prepared.values())).order_by("business_name"):
        exact_grouped.setdefault(normalize_name(entry.business_name), []).append(entry)

    result = {}
    unresolved = [name for name, norm in prepared.items() if norm not in exact_grouped]

    broad_grouped = {}
    if unresolved:
        combined_query = Q()
        for name in unresolved:
            norm = prepared[name]
            core = strip_legal_suffix(norm)
            combined_query |= _broadened_query_for(name, norm, core)

        for entry in IntermediateRegistryEntry.objects.filter(combined_query).order_by("business_name"):
            for name in unresolved:
                norm = prepared[name]
                core = strip_legal_suffix(norm)
                if _is_broadened_hit(entry.business_name, name, norm, core):
                    broad_grouped.setdefault(name, []).append(entry)

    for name, norm in prepared.items():
        if norm in exact_grouped:
            result[name] = (exact_grouped[norm], "exact_normalized")
        elif name in broad_grouped:
            result[name] = (broad_grouped[name], "broadened")
        else:
            result[name] = ([], None)

    return result


def classify_matches(matches):
    """Present / Not Present / Review Required from a resolved candidate
    list -- see models.STATUS_CHOICES. Never a separate rule from what
    "matches" itself already means: zero, exactly one, or more than one."""
    if not matches:
        return "not_present"
    if len(matches) == 1:
        return "present"
    return "review_required"
