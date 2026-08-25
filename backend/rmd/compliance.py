"""Compliance-status computations for RMD search results.

These derive display-only values from real fields already stored on
``RmdFiling`` -- they never invent or overwrite source data.
"""
from datetime import date

# Filings recertified on or after this date are considered Active.
OPERATIONAL_STATUS_THRESHOLD = date(2026, 4, 1)


def compute_operational_status(last_recertified):
    """Active/Inactive based on the real ``last_recertified`` date. No
    recertification date on file is treated as Inactive, not a separate
    "Unknown" state -- there's no evidence the filing is current."""
    if last_recertified is None:
        return "inactive"
    return "active" if last_recertified >= OPERATIONAL_STATUS_THRESHOLD else "inactive"
