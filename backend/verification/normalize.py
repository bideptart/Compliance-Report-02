"""Shared name normalization used by every cross-module company matcher.

Deliberately conservative: case folding, trimming, and internal-whitespace
collapse only. Nothing that could merge genuinely different company names.
"""
import re

from django.db.models import Value
from django.db.models.functions import Lower, Replace, Trim


_TRAILING_PUNCTUATION_RE = re.compile(r"[,;]+\s*$")


def normalize_name(value):
    if not value:
        return ""
    value = value.strip().lower()
    while "  " in value:
        value = value.replace("  ", " ")
    # A dangling trailing comma/semicolon is scrape noise, not part of the
    # company's identity -- e.g. a real FCC Form 499 page yielded the legal
    # name "TELVANTIS VOICE SERVICES INC," (trailing comma, no closing
    # word after it). Left in place, it blocks strip_legal_suffix() below
    # from recognizing "inc" as the trailing legal suffix (the regex
    # anchors the suffix to the end of the string), which in turn breaks
    # every downstream matching stage for that company. No real company
    # name legitimately ends in a bare comma, so this is safe to drop.
    value = _TRAILING_PUNCTUATION_RE.sub("", value).strip()
    return value


def normalized_name_expr(field):
    """SQL-side equivalent of normalize_name(), for filtering a queryset."""
    expr = Trim(Lower(field))
    for _ in range(3):
        expr = Replace(expr, Value("  "), Value(" "))
    return expr


# Common company-entity suffixes only -- stripping these is safe because they
# describe legal form, not the company's identity (e.g. "Bharti Airtel Ltd."
# and "Bharti Airtel Limited" are the same company; "Bharti Airtel UK
# Limited" is not, because "UK" is part of the identity, not a suffix, so it
# is deliberately left alone).
_LEGAL_SUFFIX_RE = re.compile(
    r",?\s*\b(l\.?l\.?c\.?|ltd\.?|limited|inc\.?|incorporated|corp\.?|corporation|"
    r"pte\.?\s*ltd\.?|gp|plc)\.?\s*$",
    re.IGNORECASE,
)


def contains_as_word(haystack, needle):
    """True if `needle` appears in `haystack` as a whole word/phrase, not
    embedded inside a longer word -- case-insensitive.

    This guards the substring-based matching stages against exactly the
    kind of false positive plain "contains" matching produces: a short
    carrier name like "WIC" is NOT the same company as "Twiching General
    Trading" just because the letters "wic" happen to appear inside
    "tWICHing". SQL LIKE/icontains has no concept of word boundaries, so
    it's only ever used as a cheap prefilter; this is the real check.

    Deliberately NOT implemented with regex \\b anchors: \\b only asserts a
    boundary between a word character and a non-word character, so it
    silently fails whenever the needle itself starts or ends with a
    non-word character (e.g. a legal-suffix-stripped core like
    "bharti airtel (usa)", ending in ")") and the adjacent haystack
    character is also non-word (e.g. the space before "Limited") --
    non-word-to-non-word isn't a boundary at all, so \\b never matches
    there even though the phrase is genuinely present as whole words. This
    real bug hid "Bharti Airtel (USA) Limited" from a search for
    "Bharti Airtel (USA) Ltd." even though the RMD and FCC modules'
    company-name matching agreed on every other tier. Lookaround on
    alphanumeric adjacency instead of \\b sidesteps this: it only cares
    what character (if any) sits immediately outside the match, not what
    the needle's own edge characters are.
    """
    haystack = haystack or ""
    needle = (needle or "").strip()
    if not needle:
        return False
    pattern = r"(?<![A-Za-z0-9])" + re.escape(needle) + r"(?![A-Za-z0-9])"
    return re.search(pattern, haystack, re.IGNORECASE) is not None


def strip_legal_suffix(normalized_value):
    """Iteratively removes a trailing legal-entity suffix from an already
    case/whitespace-normalized name (see normalize_name). Never used for the
    primary exact-match tier -- only as an additional, explicitly-labeled
    matching stage, so a suffix-only difference doesn't hide a real match
    without also being visible as a lower-confidence "suffix-stripped" tier.
    """
    value = normalized_value
    while True:
        stripped = _LEGAL_SUFFIX_RE.sub("", value).strip()
        stripped = re.sub(r"\s+", " ", stripped)
        if not stripped or stripped == value:
            break
        value = stripped
    return value
