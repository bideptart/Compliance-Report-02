"""Fetches the real, official RMD filing PDF straight from the FCC's own
ServiceNow-hosted Robocall Mitigation Database portal -- never a
locally-generated approximation.

The record's own filing_url (e.g.
https://fccprod.servicenowservices.com/rmd?id=rmd_form&...&sys_id=<sys_id>)
is a JavaScript-rendered page, so a plain server-side fetch of *that* URL
only returns the empty app shell. But the page itself renders a real
"Download PDF" link pointing at a plain REST attachment endpoint --
/api/x_g_fmc_rmd/rmd/attachment?sys=<sys_id> -- that serves the filer's
actual uploaded PDF with no session/auth required. This module hits that
same endpoint directly, keyed off the sys_id already stored on RmdFiling
(parsed from filing_url at import time -- see rmd.models.RmdFiling).
"""
import requests

RMD_ATTACHMENT_URL = "https://fccprod.servicenowservices.com/api/x_g_fmc_rmd/rmd/attachment"

REQUEST_TIMEOUT = 30

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*",
}


class OfficialPdfError(Exception):
    """Raised when the real official PDF can't be retrieved; carries a
    status ("not_found" or "source_unavailable") + message."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def fetch_official_pdf(sys_id):
    """(pdf_bytes, filename) for the real official filing PDF, fetched live
    from the FCC's own portal. Raises OfficialPdfError if sys_id is missing
    or the live fetch fails."""
    if not (sys_id or "").strip():
        raise OfficialPdfError("not_found", "No official filing is on file for this record.")

    try:
        response = requests.get(
            RMD_ATTACHMENT_URL, params={"sys": sys_id}, headers=_HEADERS, timeout=REQUEST_TIMEOUT
        )
    except requests.RequestException as exc:
        raise OfficialPdfError("source_unavailable", "The FCC's RMD portal could not be reached.") from exc

    if response.status_code == 404:
        raise OfficialPdfError("not_found", "No official filing PDF was found for this record.")
    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        raise OfficialPdfError("source_unavailable", "The FCC's RMD portal could not be reached.") from exc

    content_type = (response.headers.get("Content-Type") or "").lower()
    if "pdf" not in content_type or not response.content:
        raise OfficialPdfError("not_found", "No official filing PDF was found for this record.")

    filename = "filing.pdf"
    disposition = response.headers.get("Content-Disposition") or ""
    if "filename=" in disposition:
        filename = disposition.split("filename=", 1)[1].strip().strip('"') or filename

    return response.content, filename
