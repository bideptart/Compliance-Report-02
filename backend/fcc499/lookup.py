"""FCC Form 499 lookup orchestration: SQLite cache first, live FCC fetch on miss.

    FCC Form 499 Search
            v
    Check SQLite Database
            v
    Record Already Exists?
       YES ------------ NO
        v                v
    Return Data    Lookup Official Source
                          v
                     Parse Record
                          v
                     Save to SQLite
                          v
                     Return Data
"""
from __future__ import annotations

from django.db.models import Q

from . import service
from .models import Fcc499Filing

NOT_FOUND = "not_found"
SOURCE_UNAVAILABLE = "source_unavailable"
PARSE_ERROR = "parse_error"


class Fcc499LookupError(Exception):
    """Raised when a live FCC lookup fails; carries a status + message."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def find_cached(query):
    """Existing cached filings whose legal/search name matches the query."""
    query = (query or "").strip()
    if not query:
        return Fcc499Filing.objects.none()

    return Fcc499Filing.objects.filter(
        Q(legal_name__icontains=query) | Q(search_company_name__icontains=query)
    )


def _save_filing(record, company_name, detail_url):
    headquarters = record.get("headquarters") or {}

    filing, _created = Fcc499Filing.objects.update_or_create(
        filer_id=record["filerId"],
        defaults={
            "legal_name": record.get("legalName"),
            "doing_business_as": record.get("doingBusinessAs"),
            "usf_contributor": record.get("usfContributor"),
            "cores_id": record.get("coresId"),
            "registration_current_as_of": record.get("registrationCurrentAsOf"),
            "headquarters_address": headquarters.get("address"),
            "headquarters_city": headquarters.get("city"),
            "headquarters_state": headquarters.get("state"),
            "headquarters_zip": headquarters.get("zip"),
            "customer_phone": record.get("customerPhone"),
            "fcc_registration_information": record.get("fccRegistrationInformation"),
            "search_company_name": record.get("searchCompanyName") or company_name,
            "search_url": record.get("searchUrl"),
            "detail_url": detail_url,
        },
    )
    return filing


def fetch_and_cache(company_name):
    """Run the live FCC workflow for company_name and persist the result.

    Raises Fcc499LookupError with a status of NOT_FOUND, SOURCE_UNAVAILABLE,
    or PARSE_ERROR when the record can't be retrieved. Never invents data --
    only what the FCC site actually returns is saved.
    """
    try:
        record, detail_url = service.fetch_fcc_499_by_company(company_name)
    except LookupError as exc:
        raise Fcc499LookupError(NOT_FOUND, str(exc)) from exc
    except (service.requests.RequestException, OSError) as exc:
        raise Fcc499LookupError(SOURCE_UNAVAILABLE, "FCC source could not be reached.") from exc
    except (ValueError, AttributeError, TypeError) as exc:
        raise Fcc499LookupError(
            PARSE_ERROR, "FCC record was found but required fields could not be extracted."
        ) from exc

    return _save_filing(record, company_name, detail_url)


def search(query):
    """Search used by the FCC module's own search box.

    A prior version returned whatever was already cached as soon as *any*
    cached match existed, and only ever checked the live site when the
    cache had zero matches. That's wrong: the real FCC database can (and
    does) have more matching companies than whatever's happened to be
    cached before -- e.g. searching "Bharti Airtel" on the real FCC site
    returns 2 filers (826875 "Bharti Airtel (USA) Limited" and 826876
    "Bharti Airtel Limited"), but if only the first had ever been cached,
    the old logic would silently stop there and never discover the second.

    So this always re-checks the live search-results page first (one
    cheap request -- see fetch_fcc_499_filer_ids_by_company) to get the
    complete, current list of matching Filer IDs, then only fetches the
    detail page for whichever ones aren't already cached. Already-cached
    filers are reused as-is, so a repeat search doesn't re-scrape
    everything -- only genuinely new filers cost a live detail fetch.

    Returns (queryset_or_list, lookup_error_or_None). If the live search
    itself fails (source unreachable, nothing found), falls back to
    whatever is already cached rather than going empty-handed.
    """
    query = (query or "").strip()
    if not query:
        return Fcc499Filing.objects.none(), None

    try:
        filer_ids, search_url = service.fetch_fcc_499_filer_ids_by_company(query)
    except LookupError as exc:
        cached = find_cached(query)
        if cached.exists():
            return cached, None
        return Fcc499Filing.objects.none(), Fcc499LookupError(NOT_FOUND, str(exc))
    except (service.requests.RequestException, OSError):
        cached = find_cached(query)
        if cached.exists():
            return cached, None
        return Fcc499Filing.objects.none(), Fcc499LookupError(
            SOURCE_UNAVAILABLE, "FCC source could not be reached."
        )

    existing = {f.filer_id: f for f in Fcc499Filing.objects.filter(filer_id__in=filer_ids)}
    for filer_id in filer_ids:
        if filer_id in existing:
            continue
        try:
            record, detail_url = service.fetch_fcc_499_detail(filer_id)
        except (LookupError, service.requests.RequestException, OSError):
            continue
        record["searchCompanyName"] = query
        record["searchUrl"] = search_url
        record["detailUrl"] = detail_url
        try:
            existing[filer_id] = _save_filing(record, query, detail_url)
        except (ValueError, AttributeError, TypeError, KeyError):
            continue

    matched_pks = [existing[fid].pk for fid in filer_ids if fid in existing]
    if not matched_pks:
        return Fcc499Filing.objects.none(), Fcc499LookupError(
            PARSE_ERROR, "FCC records were found but could not be retrieved."
        )

    return Fcc499Filing.objects.filter(pk__in=matched_pks), None
