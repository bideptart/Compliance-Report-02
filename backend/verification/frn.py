"""The single, central FRN comparison used by the RMD, FCC Compliance, and
Customers modules -- so the same RMD/FCC company pair always produces the
same verdict everywhere, computed once in Django and never re-derived in
React.

RMD's comparable identifier is RmdFiling.frn.

FCC's comparable identifier is Fcc499Filing.cores_id -- the FCC Form 499
page's "Registration Number (CORESID)" field. This was NOT assumed: fetching
a real FCC Form 499 detail page and comparing it against the matching RMD
record for the same company (Ajoxi Limited, FRN/CORESID 0032638553 on both
sides) confirmed they are the same identifier. FCC's "499 Filer ID" is a
different, unrelated identifier (the Form 499 filing's own ID) and is never
used for this comparison.

verify_frn_match(rmd_verification, fcc_verification) expects the dict shapes
produced by verification.rmd_lookup / verification.fcc_lookup (each already
carrying a "frn" field resolved only when exactly one confirmed record
exists, plus the full "matched_records" list for every candidate found),
and returns one of:

    MATCHED               a real FRN is shared by at least one RMD candidate
                           and at least one FCC candidate
    MISMATCH              both sides have at least one real, comparable FRN,
                           and none of them are shared -- a company-name
                           match being ambiguous (several RMD and/or FCC
                           candidates) does NOT stop this comparison: every
                           real candidate FRN on both sides is checked, so
                           "multiple matches" alone is never a reason to
                           leave the FRN question unanswered
    NOT_AVAILABLE          one or both sides have no real, comparable FRN at
                           all (nothing was found, or what was found has no
                           usable FRN)
    VERIFICATION_REQUIRED  the FCC side's own data isn't in yet -- a live
                           lookup was skipped or failed (verification_pending
                           / verification_error), so there is nothing to
                           compare against, not even an ambiguous candidate.
                           RMD is a fully local, pre-imported table, so this
                           never happens on the RMD side.
"""
import re

# A plausible FCC-style registration number: digits only, realistic length.
# Guards against comparing values that exist but aren't actually shaped like
# a real FRN/CORES ID.
_FRN_SHAPE = re.compile(r"\d{6,15}")

# Only a genuinely missing FCC-side lookup blocks comparison outright.
# "multiple_matches" is NOT included here on purpose -- see _frn_candidates
# below, which cross-checks every real candidate's FRN instead of giving up.
_UNRESOLVED_STATUSES = {"verification_pending", "verification_error"}

MATCHED = "matched"
MISMATCH = "mismatch"
NOT_AVAILABLE = "not_available"
VERIFICATION_REQUIRED = "verification_required"


def _looks_like_frn(value):
    return bool(value) and bool(_FRN_SHAPE.fullmatch(value.strip()))


def _frn_candidates(verification):
    """Every real, comparable FRN across ALL of this side's matched
    records -- not just the single "frn" field, which is only populated
    when there's exactly one candidate. This is what lets an ambiguous
    company-name match (several RMD and/or FCC records with the same or
    similar name) still get a definitive FRN verdict: if any candidate on
    one side shares a real FRN with any candidate on the other, that's a
    genuine match regardless of how many other, unrelated candidates each
    side also turned up."""
    records = (verification or {}).get("matched_records") or []
    return {
        frn.strip()
        for frn in (r.get("frn") for r in records)
        if _looks_like_frn(frn)
    }


def verify_frn_match(rmd_verification, fcc_verification):
    rmd_status = (rmd_verification or {}).get("status")
    fcc_status = (fcc_verification or {}).get("status")

    rmd_frn = (rmd_verification or {}).get("frn")
    fcc_frn = (fcc_verification or {}).get("frn")

    # The FCC side's own data genuinely isn't available yet (live lookup
    # skipped or failed) -- there's nothing real to compare against at all,
    # not even an ambiguous candidate. RMD never produces this.
    if rmd_status in _UNRESOLVED_STATUSES or fcc_status in _UNRESOLVED_STATUSES:
        return {"rmd_frn": rmd_frn, "fcc_frn": fcc_frn, "status": VERIFICATION_REQUIRED}

    rmd_candidates = _frn_candidates(rmd_verification)
    fcc_candidates = _frn_candidates(fcc_verification)

    if not rmd_candidates or not fcc_candidates:
        # A confirmed "not_present" (or a match with no usable FRN on either
        # side) means there's nothing real to compare -- not a mismatch,
        # just unavailable.
        return {"rmd_frn": rmd_frn, "fcc_frn": fcc_frn, "status": NOT_AVAILABLE}

    shared = rmd_candidates & fcc_candidates
    if shared:
        matched_frn = next(iter(shared))
        return {"rmd_frn": rmd_frn or matched_frn, "fcc_frn": fcc_frn or matched_frn, "status": MATCHED}

    return {"rmd_frn": rmd_frn, "fcc_frn": fcc_frn, "status": MISMATCH}
