"""FCC Form 499 lookup/parsing logic.

Adapted from the attached FCC499_ComplianceOS_Test_Module (originally a
standalone Flask proof-of-concept). Only the actual FCC lookup/scraping
logic is reused here -- the Flask app, its in-memory "previous result" /
activity-log test state, and change-detection helpers are intentionally
left out, since persistence and history are handled by this project's
Django/SQLite + React architecture instead.

Workflow (unchanged from the original module):

    Company Name
        -> FCC Form 499 search URL
        -> Search FCC results
        -> Find matching company / Filer ID
        -> FCC 499 detail URL
        -> Parse detailed FCC record
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote, urlencode

import requests
from bs4 import BeautifulSoup

FCC_499_SEARCH_URL = "https://apps.fcc.gov/cgb/form499/499results.cfm"
FCC_499_DETAIL_URL = "https://apps.fcc.gov/cgb/form499/499detail.cfm?FilerNum={}"

REQUEST_TIMEOUT = 20

FCC_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


# ============================================================
# FCC SEARCH URL
# ============================================================

def build_fcc_499_url(company_name: str) -> str:
    """Build the FCC Form 499 search URL using a company Legal Name."""
    company_name = str(company_name or "").strip()
    if not company_name:
        raise ValueError("Company name is required.")

    params = {
        "FilerID": "",
        "frn": "",
        "operational": "",
        "comm_type": "Any Type",
        "LegalName": company_name,
        "state": "Any State",
        "R1": "and",
        "XML": "FALSE",
    }
    return FCC_499_SEARCH_URL + "?" + urlencode(params)


def build_fcc_499_detail_url(filer_number: str | int) -> str:
    """Build the FCC Form 499 detail URL for a validated Filer ID."""
    filer_number = validate_filer_number(filer_number)
    return FCC_499_DETAIL_URL.format(quote(str(filer_number), safe=""))


def validate_filer_number(filer_number: str | int) -> str:
    value = str(filer_number).strip()
    if not re.fullmatch(r"\d{1,10}", value):
        raise ValueError("Filer ID must contain 1 to 10 digits.")
    return value


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip(" :\t\r\n")


def normalize_company_name(value: str | None) -> str:
    """Normalize company names for comparison (case/spacing/punctuation)."""
    value = normalize(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _contains_phrase(haystack: str, needle: str) -> bool:
    """Whether `needle` appears in `haystack` as a contiguous whole-word
    phrase -- both already normalize_company_name()'d (lowercase,
    punctuation replaced with spaces).

    Plain substring containment is NOT enough here: normalize_company_name
    turns punctuation into spaces but doesn't add separators *inside* a
    single word, so a raw `needle in haystack` check can match across a
    word boundary that doesn't really exist -- e.g. "red telecom" is a
    literal substring of "jsquared telecom" (the "red" hides inside
    "squared"), which would wrongly match an unrelated company. Comparing
    tokenized word sequences instead avoids that.
    """
    needle_tokens = needle.split()
    if not needle_tokens:
        return False
    haystack_tokens = haystack.split()
    n = len(needle_tokens)
    return any(haystack_tokens[i : i + n] == needle_tokens for i in range(len(haystack_tokens) - n + 1))


def _all_text_lines(soup: BeautifulSoup) -> list[str]:
    text = soup.get_text("\n", strip=True)
    return [normalize(line) for line in text.splitlines() if normalize(line)]


def _find_value(lines: list[str], labels: list[str]) -> str | None:
    normalized_labels = [normalize(label).lower().rstrip(":") for label in labels]

    for index, line in enumerate(lines):
        low = line.lower().rstrip(":")
        for label in normalized_labels:
            if low == label:
                if index + 1 < len(lines):
                    candidate = lines[index + 1]
                    candidate_low = candidate.lower().rstrip(":")
                    if candidate_low not in normalized_labels:
                        return candidate
            if low.startswith(label + ":"):
                candidate = normalize(line[len(label) + 1 :])
                if candidate:
                    return candidate
    return None


def _find_value_from_tables(soup: BeautifulSoup, labels: list[str]) -> str | None:
    normalized_labels = [normalize(label).lower().rstrip(":") for label in labels]

    for row in soup.find_all("tr"):
        cells = [normalize(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        cells = [cell for cell in cells if cell]

        for index, cell in enumerate(cells):
            low = cell.lower().rstrip(":")
            if low in normalized_labels:
                if index + 1 < len(cells):
                    return cells[index + 1]
                if ":" in cell:
                    return normalize(cell.split(":", 1)[1])
    return None


def _value(soup: BeautifulSoup, lines: list[str], labels: list[str]) -> str | None:
    return _find_value_from_tables(soup, labels) or _find_value(lines, labels)


def _extract_filer_id_from_href(href: str) -> str | None:
    if not href:
        return None
    match = re.search(r"(?:FilerNum|FilerID)=(\d+)", href, re.IGNORECASE)
    if match:
        return validate_filer_number(match.group(1))
    return None


# ============================================================
# FIND ALL MATCHING FILER IDS IN SEARCH RESULTS
# ============================================================

def find_all_filer_ids_in_search_results(html: str, company_name: str, limit: int = 10) -> list[str]:
    """Every distinct Filer ID in the search results whose row phrase-matches
    company_name -- not just the single best one. A broad search like
    "Bharti Airtel" can legitimately match several real, separate companies
    ("Bharti Airtel Ltd.", "Bharti Airtel (USA) Ltd.", "Bharti Airtel UK
    Limited"); collapsing that down to one is exactly the false-consolidation
    bug this function exists to avoid. Order follows the FCC page's own
    result order, deduplicated by Filer ID, capped at `limit`."""
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    requested_name = normalize_company_name(company_name)
    if not requested_name:
        return []

    filer_ids: list[str] = []
    seen: set[str] = set()

    for row in soup.find_all("tr"):
        row_text = normalize(row.get_text(" ", strip=True))
        normalized_row = normalize_company_name(row_text)
        if not normalized_row or not _contains_phrase(normalized_row, requested_name):
            continue

        filer_id = None
        for link in row.find_all("a"):
            filer_id = _extract_filer_id_from_href(link.get("href") or "")
            if filer_id:
                break
        if not filer_id:
            cells = [normalize(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"])]
            for cell in cells:
                if re.fullmatch(r"\d{1,10}", cell):
                    try:
                        filer_id = validate_filer_number(cell)
                        break
                    except ValueError:
                        continue

        if filer_id and filer_id not in seen:
            seen.add(filer_id)
            filer_ids.append(filer_id)
            if len(filer_ids) >= limit:
                break

    return filer_ids


# ============================================================
# FIND FILER ID IN SEARCH RESULTS
# ============================================================

def find_filer_id_in_search_results(html: str, company_name: str) -> str:
    """Search FCC Form 499 results HTML for the Filer ID of a matching row."""
    if not html:
        raise LookupError("FCC search returned an empty response.")

    soup = BeautifulSoup(html, "html.parser")
    requested_name = normalize_company_name(company_name)
    if not requested_name:
        raise ValueError("Company name is required.")

    # METHOD 0: an exact -- or leading-prefix -- match on the Legal Name
    # column beats every looser method below. Search results commonly
    # include unrelated companies whose *Doing Business As* merely contains
    # the search term (e.g. searching "Telin" also surfaces "Telekomunikasi
    # Indonesia International (USA), Inc." via its DBA "Telin USA") -- when
    # the actual company is also present under its own Legal Name starting
    # with the search term (e.g. "Telin Systems LLC"), that's the real
    # match, not the DBA-based one.
    def _legal_name_row_filer_id(require_exact: bool) -> str | None:
        for row in soup.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            legal_name_cell = normalize_company_name(normalize(cells[1].get_text(" ", strip=True)))
            if not legal_name_cell:
                continue
            legal_tokens = legal_name_cell.split()
            requested_tokens = requested_name.split()
            is_match = (
                legal_tokens == requested_tokens
                if require_exact
                else legal_tokens[: len(requested_tokens)] == requested_tokens
            )
            if not is_match:
                continue
            for link in row.find_all("a"):
                filer_id = _extract_filer_id_from_href(link.get("href") or "")
                if filer_id:
                    return filer_id
            first_cell = normalize(cells[0].get_text(" ", strip=True))
            if re.fullmatch(r"\d{1,10}", first_cell):
                try:
                    return validate_filer_number(first_cell)
                except ValueError:
                    pass
        return None

    filer_id = _legal_name_row_filer_id(require_exact=True) or _legal_name_row_filer_id(require_exact=False)
    if filer_id:
        return filer_id

    # METHOD 1: search table rows
    for row in soup.find_all("tr"):
        row_text = normalize(row.get_text(" ", strip=True))
        normalized_row = normalize_company_name(row_text)
        if not normalized_row or not _contains_phrase(normalized_row, requested_name):
            continue

        for link in row.find_all("a"):
            filer_id = _extract_filer_id_from_href(link.get("href") or "")
            if filer_id:
                return filer_id

        cells = [normalize(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"])]
        for cell in cells:
            if re.fullmatch(r"\d{1,10}", cell):
                try:
                    return validate_filer_number(cell)
                except ValueError:
                    pass

    # METHOD 2: search all links
    for link in soup.find_all("a"):
        link_text = normalize(link.get_text(" ", strip=True))
        filer_id = _extract_filer_id_from_href(link.get("href") or "")
        if not filer_id:
            continue
        if _contains_phrase(normalize_company_name(link_text), requested_name):
            return filer_id

    # METHOD 3: search parent/container around FilerNum links
    for link in soup.find_all("a"):
        filer_id = _extract_filer_id_from_href(link.get("href") or "")
        if not filer_id:
            continue

        parent = link.parent
        if parent:
            parent_text = normalize(parent.get_text(" ", strip=True))
            if _contains_phrase(normalize_company_name(parent_text), requested_name):
                return filer_id

        ancestor = link
        for _ in range(2):
            ancestor = ancestor.parent
            if not ancestor:
                break
            ancestor_text = normalize(ancestor.get_text(" ", strip=True))
            if _contains_phrase(normalize_company_name(ancestor_text), requested_name):
                return filer_id

    # METHOD 4: search page text around company name
    lines = _all_text_lines(soup)
    for index, line in enumerate(lines):
        normalized_line = normalize_company_name(line)
        if not _contains_phrase(normalized_line, requested_name):
            continue

        nearby_lines = lines[max(0, index - 2) : min(len(lines), index + 6)]
        nearby_text = " ".join(nearby_lines)

        patterns = [
            r"Filer\s*ID\s*[:#]?\s*(\d{1,10})",
            r"499\s*Filer\s*ID\s*[:#]?\s*(\d{1,10})",
            r"FilerNum\s*[:=]\s*(\d{1,10})",
            r"FilerID\s*[:=]\s*(\d{1,10})",
        ]
        for pattern in patterns:
            match = re.search(pattern, nearby_text, re.IGNORECASE)
            if match:
                return validate_filer_number(match.group(1))

    # METHOD 5: search HTML for FilerNum + company proximity
    normalized_html = normalize_company_name(soup.get_text(" ", strip=True))
    if _contains_phrase(normalized_html, requested_name):
        for match in re.finditer(r"(?:FilerNum|FilerID)=(\d{1,10})", html, re.IGNORECASE):
            filer_id = match.group(1)
            start = max(0, match.start() - 1000)
            end = min(len(html), match.end() + 1000)
            nearby_html = html[start:end]
            nearby_text = BeautifulSoup(nearby_html, "html.parser").get_text(" ", strip=True)
            if _contains_phrase(normalize_company_name(nearby_text), requested_name):
                return validate_filer_number(filer_id)

    raise LookupError(f'FCC 499 company "{company_name}" was not found in the FCC search results.')


# ============================================================
# PARSE FCC 499 DETAIL HTML
# ============================================================

def parse_fcc_499_html(html: str, filer_number: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    lines = _all_text_lines(soup)
    body_text = " ".join(lines).lower()

    not_found_markers = [
        "record not found",
        "no record found",
        "filer not found",
        "invalid filer",
        "no filer information",
    ]
    if any(marker in body_text for marker in not_found_markers):
        raise LookupError("FCC 499 record not found.")

    record = {
        "filerId": _value(soup, lines, ["499 Filer ID", "Filer 499 ID", "Filer ID"]) or filer_number,
        "registrationCurrentAsOf": _value(
            soup, lines, ["Registration Current As Of", "Registration Current as of", "Registration Current As Of:"]
        ),
        "legalName": _value(
            soup, lines, ["Legal Name of Reporting Entity", "Legal Name of Filer", "Legal Name"]
        ),
        "doingBusinessAs": _value(
            soup, lines, ["Doing Business As", "DBA", "Doing Business As (DBA)"]
        ),
        "usfContributor": _value(
            soup, lines, ["Universal Service Fund Contributor", "USF Contributor", "Universal Service Fund"]
        ),
        "coresId": _value(
            soup,
            lines,
            [
                # Confirmed against the real, live FCC Form 499 detail page --
                # this is the actual label used there.
                "Registration Number (CORESID)",
                "Registration Number (CORES ID)",
                "Registration Number / CORESID",
                "Registration Number / CORES ID",
                "CORESID",
                "CORES ID",
                "FRN",
            ],
        ),
        "headquarters": {
            "address": _value(
                soup, lines, ["Headquarters Address", "Corporate Headquarters Address", "Headquarters Street Address"]
            ),
            "city": _value(soup, lines, ["Headquarters City"]),
            "state": _value(soup, lines, ["Headquarters State"]),
            "zip": _value(soup, lines, ["Headquarters ZIP", "Headquarters Zip", "ZIP Code", "Zip Code", "ZIP"]),
        },
        "customerPhone": _value(
            soup, lines, ["Customer Inquiries Telephone", "Customer Inquiries Phone", "Customer Telephone"]
        ),
        "fccRegistrationInformation": _value(
            soup, lines, ["FCC Registration Information", "Registration Information"]
        ),
    }

    record["filerId"] = validate_filer_number(record["filerId"])

    required_core = ["filerId", "registrationCurrentAsOf", "legalName"]
    missing_fields = [field for field in required_core if not normalize(record.get(field))]
    if missing_fields:
        raise ValueError("Required FCC fields could not be extracted reliably: " + ", ".join(missing_fields))

    return record


# ============================================================
# NETWORK FETCH
# ============================================================

def fetch_fcc_499_search(company_name: str) -> tuple[str, str]:
    url = build_fcc_499_url(company_name)
    response = requests.get(url, headers=FCC_HEADERS, timeout=REQUEST_TIMEOUT)

    if response.status_code == 404:
        raise LookupError("FCC 499 search page not found.")
    response.raise_for_status()

    if not response.text.strip():
        raise LookupError("FCC returned an empty search response.")

    return response.text, url


def fetch_fcc_499_detail(filer_number: str) -> tuple[dict[str, Any], str]:
    filer_number = validate_filer_number(filer_number)
    url = build_fcc_499_detail_url(filer_number)
    response = requests.get(url, headers=FCC_HEADERS, timeout=REQUEST_TIMEOUT)

    if response.status_code == 404:
        raise LookupError("FCC 499 record not found.")
    response.raise_for_status()

    if not response.text.strip():
        raise LookupError("FCC returned an empty detail response.")

    record = parse_fcc_499_html(response.text, filer_number)
    return record, url


def fetch_fcc_499_by_company(company_name: str) -> tuple[dict[str, Any], str]:
    """Full workflow: company name -> search -> Filer ID -> detail record."""
    company_name = normalize(company_name)
    if not company_name:
        raise ValueError("Company name is required.")

    search_html, search_url = fetch_fcc_499_search(company_name)
    filer_id = find_filer_id_in_search_results(search_html, company_name)
    record, detail_url = fetch_fcc_499_detail(filer_id)

    record["searchCompanyName"] = company_name
    record["searchUrl"] = search_url
    record["detailUrl"] = detail_url

    return record, detail_url


def fetch_fcc_499_filer_ids_by_company(company_name: str, limit: int = 25) -> tuple[list[str], str]:
    """Just the search step: company name -> every matching Filer ID
    currently on the live FCC search results page (real FCC data can gain
    or lose filers over time, so this is always freshly checked, never
    assumed from a prior fetch). Cheap -- one request, no per-filer detail
    fetches -- so callers can compare against what's already cached and
    only fetch detail pages for genuinely new filers."""
    company_name = normalize(company_name)
    if not company_name:
        raise ValueError("Company name is required.")

    search_html, search_url = fetch_fcc_499_search(company_name)
    filer_ids = find_all_filer_ids_in_search_results(search_html, company_name, limit=limit)
    if not filer_ids:
        raise LookupError(f'FCC 499 company "{company_name}" was not found in the FCC search results.')

    return filer_ids, search_url

    return results
