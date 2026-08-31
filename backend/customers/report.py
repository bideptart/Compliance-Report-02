"""Generates the per-customer onboarding/compliance checklist PDF (same
sections/format as the reference TeleComply Compliance Suite report),
populated entirely from this customer's real RMD, FCC Form 499,
Intermediate Provider Registry, and Agreements data. Fields with no real
data on file are reported as "Not on file" / "Not available" rather than
guessed or invented.
"""
import io
import logging
import os

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from fcc499.models import Fcc499Filing
from intermediate_registry.models import IntermediateRegistryRecord
from rmd.compliance import OPERATIONAL_STATUS_THRESHOLD
from rmd.models import RmdFiling
from verification.customer import get_customer_verification

logger = logging.getLogger(__name__)

# Extracted once from the real mcm-logo.pdf asset, then given a transparent
# background (its own blank canvas removed; the icon's own white card and
# the MCM text/bars are untouched) -- a project-relative path, never a
# machine-specific one, so this keeps working wherever the repo is checked
# out. mcm-logo.png (opaque) is kept alongside it as the untouched source
# if the transparent version ever needs regenerating.
MCM_LOGO_PATH = os.path.join(os.path.dirname(__file__), "branding", "mcm-logo-transparent.png")
MCM_LOGO_MAX_WIDTH = 1.1 * inch
MCM_LOGO_MAX_HEIGHT = 0.45 * inch

NAVY = colors.HexColor("#1B3A5C")
LIGHT_BLUE = colors.HexColor("#EAF2FA")
HEADER_GRAY = colors.HexColor("#F2F4F6")
ROW_ALT = colors.HexColor("#F7F9FB")
BORDER = colors.HexColor("#D9E0E6")
TEXT_MUTED = colors.HexColor("#6B7684")
# Same success/warning/danger hexes as the app's own --color-success/
# --color-warning/--color-danger (src/index.css) -- the PDF's status colors
# match the same design language as the React UI, not an invented palette.
SUCCESS = colors.HexColor("#15803D")
WARNING = colors.HexColor("#B45309")
DANGER = colors.HexColor("#B91C1C")

NOT_ON_FILE = "Not on file"
NOT_AVAILABLE = "Not available"

PRESENCE_LABELS = {
    "present": "PRESENT",
    "not_present": "NOT PRESENT",
    "multiple_matches": "MULTIPLE MATCHES — needs resolution",
    "verification_pending": "VERIFICATION PENDING",
    "verification_error": "VERIFICATION ERROR",
}
FRN_STATUS_LABELS = {
    "matched": "MATCHED",
    "mismatch": "MISMATCH",
    "not_available": "NOT AVAILABLE",
    "verification_required": "VERIFICATION REQUIRED",
}

_styles = getSampleStyleSheet()
TITLE_STYLE = ParagraphStyle("ReportTitle", parent=_styles["Title"], alignment=TA_LEFT, fontSize=20, textColor=NAVY, spaceAfter=4)
SECTION_TITLE_STYLE = ParagraphStyle("SectionTitle", parent=_styles["Heading2"], textColor=colors.white, fontSize=11, leading=14)
# Plain underlined heading style -- unlike the numbered checklist sections
# (solid navy bar, see _section_bar), the reference report's "At-a-Glance
# Summary" heading is plain navy text with a thin rule underneath, not a
# filled box.
UNDERLINED_HEADING_STYLE = ParagraphStyle("UnderlinedHeading", parent=_styles["Heading2"], textColor=NAVY, fontSize=13, spaceAfter=0)
HEADER_CELL_STYLE = ParagraphStyle("HeaderCell", parent=_styles["Normal"], fontSize=8.5, leading=11, textColor=colors.white, fontName="Helvetica-Bold")
CELL_STYLE = ParagraphStyle("Cell", parent=_styles["Normal"], fontSize=8.5, leading=11)
CELL_BOLD = ParagraphStyle("CellBold", parent=CELL_STYLE, fontName="Helvetica-Bold")
CELL_MUTED = ParagraphStyle("CellMuted", parent=CELL_STYLE, textColor=TEXT_MUTED)
CELL_SUCCESS = ParagraphStyle("CellSuccess", parent=CELL_STYLE, textColor=SUCCESS, fontName="Helvetica-Bold")
CELL_WARNING = ParagraphStyle("CellWarning", parent=CELL_STYLE, textColor=WARNING, fontName="Helvetica-Bold")
CELL_DANGER = ParagraphStyle("CellDanger", parent=CELL_STYLE, textColor=DANGER, fontName="Helvetica-Bold")
NOTE_STYLE = ParagraphStyle("Note", parent=_styles["Normal"], fontSize=8.5, textColor=NAVY, leading=11, fontName="Helvetica-Oblique")
INTRO_STYLE = ParagraphStyle("Intro", parent=_styles["Normal"], fontSize=8.5, textColor=TEXT_MUTED, leading=11, spaceAfter=6, fontName="Helvetica-Oblique")
FOOTER_STYLE = ParagraphStyle("Footer", parent=_styles["Normal"], fontSize=7.5, textColor=TEXT_MUTED, leading=10)
SOURCES_HEADING_STYLE = ParagraphStyle("SourcesHeading", parent=_styles["Heading2"], textColor=NAVY, fontSize=12, spaceAfter=6)
SOURCES_ITEM_STYLE = ParagraphStyle("SourcesItem", parent=_styles["Normal"], fontSize=8.5, leading=13, spaceAfter=2)


def _p(value, style=CELL_STYLE):
    text = value if value not in (None, "") else "—"
    return Paragraph(str(text).replace("\n", "<br/>"), style)


def _mcm_logo_flowable():
    """The MCM logo sized to fit the header while keeping its original
    aspect ratio -- returns None (never raises) when the asset is missing
    or unreadable, so a report still generates without the logo rather
    than failing outright; the missing/broken asset is logged so it stays
    visible during local testing."""
    if not os.path.isfile(MCM_LOGO_PATH):
        logger.warning("MCM logo asset not found at %s -- generating PDF without it.", MCM_LOGO_PATH)
        return None
    try:
        natural_width, natural_height = ImageReader(MCM_LOGO_PATH).getSize()
    except Exception:
        logger.exception("MCM logo asset at %s could not be read -- generating PDF without it.", MCM_LOGO_PATH)
        return None

    scale = min(MCM_LOGO_MAX_WIDTH / natural_width, MCM_LOGO_MAX_HEIGHT / natural_height)
    return Image(MCM_LOGO_PATH, width=natural_width * scale, height=natural_height * scale)


def _section_bar(title):
    table = Table([[Paragraph(title, SECTION_TITLE_STYLE)]], colWidths=[7.3 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _checklist_table(rows, col_widths=(2.3 * inch, 3.9 * inch, 1.1 * inch)):
    data = [[Paragraph("Checklist Item", HEADER_CELL_STYLE), Paragraph("Finding", HEADER_CELL_STYLE), Paragraph("Source", HEADER_CELL_STYLE)]]
    for item, finding, source in rows:
        data.append([_p(item, CELL_BOLD), _p(finding), _p(source, CELL_MUTED)])

    table = Table(data, colWidths=list(col_widths), repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(2, len(data), 2):
        style.append(("BACKGROUND", (0, i), (-1, i), ROW_ALT))
    table.setStyle(TableStyle(style))
    return table


def _summary_table(rows):
    """Each row is (label, value) or (label, value, style) -- style colors
    the value cell (see _tone_for_* helpers) to match the reference report's
    color-coded status values (green/amber/red), defaulting to plain text
    when no tone applies."""
    data = [[_p(row[0], CELL_BOLD), _p(row[1], row[2] if len(row) > 2 else CELL_STYLE)] for row in rows]
    table = Table(data, colWidths=[2.3 * inch, 5.0 * inch])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), HEADER_GRAY),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _note_box(text):
    table = Table([[Paragraph(text, NOTE_STYLE)]], colWidths=[7.3 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _fmt_date(value):
    return value.isoformat() if value else "—"


def _flatten_address(value):
    """Join a multi-line source address into one comma-separated line, the
    same single-line style the reference report uses -- source data (e.g.
    RmdFiling.business_address) sometimes carries embedded newlines that
    would otherwise force an unwanted hard line break in the PDF."""
    if not value:
        return value
    lines = [line.strip().rstrip(",") for line in value.splitlines() if line.strip()]
    return ", ".join(lines)


def _get_rmd_record(customer, result):
    if customer.linked_rmd_record_id:
        return customer.linked_rmd_record
    record_id = result["rmd_verification"].get("record_id")
    return RmdFiling.objects.filter(pk=record_id).first() if record_id else None


def _get_fcc_record(customer, result):
    if customer.linked_fcc_record_id:
        return customer.linked_fcc_record
    record_id = result["fcc_verification"].get("record_id")
    return Fcc499Filing.objects.filter(pk=record_id).first() if record_id else None


def _get_registry_record(customer):
    return IntermediateRegistryRecord.objects.select_related("matched_entry").filter(customer=customer).first()


def _fcc_address(fcc_record):
    if not fcc_record:
        return None
    parts = [p for p in (fcc_record.headquarters_address, fcc_record.headquarters_city, fcc_record.headquarters_state, fcc_record.headquarters_zip) if p]
    return ", ".join(parts) if parts else None


def _principal_address(rmd_record, registry_entry, fcc_record):
    address = (
        (rmd_record.business_address if rmd_record else None)
        or (registry_entry.business_address if registry_entry else None)
        or _fcc_address(fcc_record)
    )
    return _flatten_address(address)


def _source_for(rmd_status, fcc_status):
    sources = []
    if rmd_status == "present":
        sources.append("RMD")
    if fcc_status == "present":
        sources.append("FCC")
    return " / ".join(sources) if sources else "Not on file"


def _frn_display(frn_verification):
    frn = frn_verification.get("rmd_frn") or frn_verification.get("fcc_frn")
    if not frn:
        return NOT_ON_FILE
    status = frn_verification["status"]
    if status == "matched":
        return f"{frn} (matches on both RMD and FCC Form 499 filings)"
    if status == "mismatch":
        return f"RMD: {frn_verification.get('rmd_frn') or '—'} / FCC: {frn_verification.get('fcc_frn') or '—'} (MISMATCH)"
    return frn


def _dba_names(rmd_record, fcc_record):
    names = []
    if rmd_record and rmd_record.other_dba_names:
        names.append(rmd_record.other_dba_names)
    if fcc_record and fcc_record.doing_business_as:
        names.append(fcc_record.doing_business_as)
    return "; ".join(dict.fromkeys(names)) if names else "No DBA/trade name on file."


def _registration_ids(result, rmd_record):
    parts = []
    if result["filer_id"]:
        parts.append(f"FCC Filer ID {result['filer_id']}")
    frn = result["frn_verification"].get("fcc_frn") or result["frn_verification"].get("rmd_frn")
    if frn:
        parts.append(f"FRN/CORES ID {frn}")
    if rmd_record:
        parts.append(f"RMD Filing Number {rmd_record.number}")
    return "; ".join(parts) if parts else NOT_ON_FILE


def _primary_contact(rmd_record, fcc_record):
    parts = []
    if fcc_record and fcc_record.customer_phone:
        parts.append(f"FCC contact phone {fcc_record.customer_phone}")
    if rmd_record and rmd_record.robocall_mitigation_contact_name:
        bits = [rmd_record.robocall_mitigation_contact_name]
        if rmd_record.contact_title:
            bits.append(rmd_record.contact_title)
        if rmd_record.contact_telephone_number:
            bits.append(rmd_record.contact_telephone_number)
        parts.append("RMD contact " + ", ".join(bits))
    return " / ".join(parts) if parts else NOT_ON_FILE


def _compliance_contact(rmd_record, registry_entry):
    if not rmd_record or not rmd_record.robocall_mitigation_contact_name:
        return NOT_ON_FILE
    bits = [rmd_record.robocall_mitigation_contact_name]
    if rmd_record.contact_title:
        bits.append(rmd_record.contact_title)
    if rmd_record.contact_telephone_number:
        bits.append(rmd_record.contact_telephone_number)
    text = ", ".join(bits)
    if (
        registry_entry
        and registry_entry.regulatory_contact_name
        and registry_entry.regulatory_contact_name.strip().lower() != rmd_record.robocall_mitigation_contact_name.strip().lower()
    ):
        registry_bits = [registry_entry.regulatory_contact_name]
        if registry_entry.regulatory_contact_title:
            registry_bits.append(registry_entry.regulatory_contact_title)
        text += f" — differs from the Intermediate Provider Registry's regulatory contact ({', '.join(registry_bits)})."
    return text


def _provider_role(rmd_record):
    if not rmd_record:
        return NOT_ON_FILE
    return (
        f"Voice Service Provider = {rmd_record.voice_service_provider_choice or '—'}, "
        f"Gateway = {rmd_record.gateway_provider_choice or '—'}, "
        f"Intermediate = {rmd_record.intermediate_provider_choice or '—'}."
    )


def _rmd_certification_summary(rmd_record):
    if not rmd_record:
        return NOT_ON_FILE
    bits = []
    if rmd_record.implementation:
        bits.append(f'STIR/SHAKEN: "{rmd_record.implementation}"')
    if rmd_record.foreign_voice_provider:
        bits.append(f"Foreign Voice Provider: {rmd_record.foreign_voice_provider}")
    return "; ".join(bits) if bits else "No material concerns flagged in the filing."


def _recertification_currency(rmd_record):
    if rmd_record is None or rmd_record.last_recertified is None:
        return "Not available — no RMD recertification date on file."
    if rmd_record.last_recertified >= OPERATIONAL_STATUS_THRESHOLD:
        return f"CURRENT (last recertified {rmd_record.last_recertified.isoformat()})"
    return f"FLAGGED - stale (last recertified {rmd_record.last_recertified.isoformat()}, before threshold {OPERATIONAL_STATUS_THRESHOLD.isoformat()})"


def _removal_confirmation(rmd_record, rmd_status):
    if rmd_status != "present" or not rmd_record:
        return "Not confirmed — no single resolved RMD filing on file for this customer."
    if rmd_record.last_recertified and rmd_record.last_recertified >= OPERATIONAL_STATUS_THRESHOLD:
        return "Present as an active, current RMD filing entry."
    return "Present as an active RMD filing entry, but flagged for a stale recertification date (see RMD Recertification Currency above) — not an FCC removal/suspension."


def _identity_legitimacy(frn_verification, rmd_status, fcc_status):
    if frn_verification["status"] == "matched":
        return "Confirmed and cross-linked by the same FRN on independent RMD/FCC records."
    if rmd_status == "present" and fcc_status == "present":
        return "Present on both RMD and FCC, but the FRN comparison did not confirm a match — see FRN Cross-Match above."
    return "Not independently cross-confirmed — one or both of RMD/FCC presence is unresolved."


def _intermediate_self_report(rmd_record):
    if not rmd_record:
        return NOT_ON_FILE
    choice = rmd_record.intermediate_provider_choice or "—"
    if choice.strip().lower() == "yes":
        return "RMD self-report: Intermediate Provider = Yes."
    return f"RMD self-report: Intermediate Provider = {choice}, suggesting it serves its own end customers (self-reported, unconfirmed)."


def _designated_contact(rmd_record):
    if not rmd_record or not rmd_record.robocall_mitigation_contact_name:
        return NOT_ON_FILE
    bits = [rmd_record.robocall_mitigation_contact_name]
    if rmd_record.contact_title:
        bits.append(rmd_record.contact_title)
    if rmd_record.contact_telephone_number:
        bits.append(rmd_record.contact_telephone_number)
    return ", ".join(bits) + " on file — confirm current before relying on it for urgent escalations."


def _compliance_reasons(result):
    reasons = []
    rmd_status = result["rmd_verification"]["status"]
    fcc_status = result["fcc_verification"]["status"]
    frn_status = result["frn_verification"]["status"]
    registry_status = result["intermediate_registry_status"]
    compliance = result["compliance"]

    if rmd_status == "not_present":
        reasons.append("Not found in the RMD dataset")
    elif rmd_status == "multiple_matches":
        reasons.append("RMD match is ambiguous (multiple candidates) — needs resolution in the Customers module")

    if fcc_status == "not_present":
        reasons.append("No FCC Form 499 record found")
    elif fcc_status == "multiple_matches":
        reasons.append("FCC Form 499 match is ambiguous (multiple candidates) — needs resolution in the Customers module")
    elif fcc_status == "verification_pending":
        reasons.append("FCC Form 499 lookup pending/not yet cached")
    elif compliance.get("not_active"):
        reasons.append("FCC Form 499 registration is not current (Inactive)")

    if compliance.get("no_filer_id"):
        reasons.append("No FCC Filer ID on file")

    if frn_status == "mismatch":
        reasons.append("FRN does not match between RMD and FCC")
    elif frn_status == "not_available":
        reasons.append("FRN not comparable (missing on one or both sides)")
    elif frn_status == "verification_required":
        reasons.append("FRN comparison pending FCC verification")

    if registry_status != "present":
        reasons.append(f"Intermediate Provider Registry status: {result['intermediate_registry_status_label']}")

    return reasons


def _compliance_summary(result):
    if result["compliance"]["fully_compliant"]:
        return "FULLY COMPLIANT (per current thresholds)"
    reasons = _compliance_reasons(result)
    return "NOT FULLY COMPLIANT — " + ("; ".join(reasons) if reasons else "one or more required checks unresolved")


def _tone_for_presence(status):
    if status == "present":
        return CELL_SUCCESS
    if status == "not_present":
        return CELL_DANGER
    if status in ("multiple_matches", "review_required"):
        return CELL_WARNING
    return CELL_STYLE


def _tone_for_frn(status):
    if status == "matched":
        return CELL_SUCCESS
    if status == "mismatch":
        return CELL_DANGER
    if status in ("not_available", "verification_required"):
        return CELL_WARNING
    return CELL_STYLE


def _tone_for_recertification(text):
    if text.startswith("FLAGGED"):
        return CELL_WARNING
    if text.startswith("CURRENT"):
        return CELL_SUCCESS
    return CELL_STYLE


def _agreement_summary(agreements):
    if not agreements:
        return "No agreement on file in the Agreements module for this customer yet."
    active = [a for a in agreements if a.compute_status() in ("active", "expiring_soon")]
    chosen = active[0] if active else agreements[0]
    status_label = chosen.compute_status().replace("_", " ").title()
    suffix = "" if active else " (not currently active)"
    return f"{chosen.agreement_title} ({chosen.agreement_id}) — status: {status_label}, effective {chosen.effective_date.isoformat()}{suffix}."


def _final_approval(result):
    if result["compliance"]["fully_compliant"]:
        return f"Marked Fully Compliant by this Suite's automated checks as of {timezone.localdate().isoformat()}."
    return "Not yet — see Overall Compliance Suite Status in the At-a-Glance Summary above."


def generate_customer_report_pdf(customer):
    """Returns the PDF report for this customer as raw bytes."""
    result = get_customer_verification(customer, allow_live_fcc_fetch=True)
    rmd_status = result["rmd_verification"]["status"]
    fcc_status = result["fcc_verification"]["status"]
    frn_verification = result["frn_verification"]

    rmd_record = _get_rmd_record(customer, result)
    fcc_record = _get_fcc_record(customer, result)
    registry_record = _get_registry_record(customer)
    registry_entry = registry_record.matched_entry if registry_record and registry_record.status == "present" else None
    agreements = list(customer.agreements.order_by("-created_at")[:5])

    company_name = result["company_name"] or customer.carrier
    principal_address = _principal_address(rmd_record, registry_entry, fcc_record)
    today = timezone.localdate().isoformat()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"{company_name} - Onboarding Checklist",
    )

    story = []
    logo = _mcm_logo_flowable()
    if logo is not None:
        # Independent, right-aligned block sitting above the title -- not
        # beside it -- with its own breathing room before the title starts,
        # rather than sharing the title's row.
        logo.hAlign = "RIGHT"
        story.append(logo)
        story.append(Spacer(1, 10))

    # Same title Paragraph/style as always -- unwrapped, at the left margin,
    # unaffected by whether a logo was placed above it.
    story.append(Paragraph(company_name, TITLE_STYLE))
    story.append(HRFlowable(width="100%", thickness=1.2, color=NAVY, spaceAfter=10))

    recertification_text = _recertification_currency(rmd_record)
    compliance_text = _compliance_summary(result)
    story.append(Paragraph("At-a-Glance Summary", UNDERLINED_HEADING_STYLE))
    story.append(HRFlowable(width="100%", thickness=0.75, color=NAVY, spaceAfter=8))
    story.append(
        _summary_table(
            [
                ("Legal Name", company_name),
                ("FRN", _frn_display(frn_verification)),
                ("FCC Filer ID (Form 499)", result["filer_id"] or NOT_ON_FILE),
                ("RMD Filing Number", rmd_record.number if rmd_record else NOT_ON_FILE),
                ("Principal Address", principal_address or NOT_ON_FILE),
                ("RMD Presence", PRESENCE_LABELS.get(rmd_status, rmd_status.upper()), _tone_for_presence(rmd_status)),
                ("FCC Form 499 Presence", PRESENCE_LABELS.get(fcc_status, fcc_status.upper()), _tone_for_presence(fcc_status)),
                (
                    "Intermediate Provider Registry",
                    result["intermediate_registry_status_label"],
                    _tone_for_presence(result["intermediate_registry_status"]),
                ),
                (
                    "FRN Cross-Match (RMD vs FCC)",
                    FRN_STATUS_LABELS.get(frn_verification["status"], frn_verification["status"]),
                    _tone_for_frn(frn_verification["status"]),
                ),
                ("RMD Recertification Currency", recertification_text, _tone_for_recertification(recertification_text)),
                ("Overall Compliance Suite Status", compliance_text),
            ]
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        _note_box(
            'Note: "Inactive" recertification is this Compliance Suite\'s own recency flag, not an FCC removal/suspension — '
            "ask the provider to recertify."
        )
    )
    story.append(Spacer(1, 16))

    story.append(_section_bar("1. Company Identification"))
    story.append(
        _checklist_table(
            [
                ("Exact legal company name", company_name, _source_for(rmd_status, fcc_status)),
                ("All DBA/trade names", _dba_names(rmd_record, fcc_record), "RMD / FCC"),
                ("Principal business address", principal_address or NOT_ON_FILE, "RMD / IPR / FCC"),
                ("Country of incorporation/organization", result["country"] or NOT_ON_FILE, "RMD"),
                ("Company registration/incorporation information", _registration_ids(result, rmd_record), "FCC / RMD"),
                ("Company website", NOT_ON_FILE + " — requires direct outreach.", "Not on file"),
                ("Primary business contact information", _primary_contact(rmd_record, fcc_record), "FCC / RMD"),
                ("Compliance/abuse contact information", _compliance_contact(rmd_record, registry_entry), "RMD / IPR"),
                ("Nature of the provider's telecommunications business", "Not stated as free text; see service-type classification below.", "RMD"),
                ("Voice service provider / intermediate provider / other carrier", _provider_role(rmd_record), "RMD"),
            ]
        )
    )
    story.append(Spacer(1, 16))

    story.append(_section_bar("2. FCC / RMD Verification"))
    story.append(
        _checklist_table(
            [
                (
                    "[FCC] Whether the provider will send traffic using U.S. NANP resources in the caller-ID field",
                    NOT_AVAILABLE + " — filings don't capture per-call signaling; needs direct technical inquiry.",
                    "Not on file",
                ),
                (
                    "Verify the provider appears in the FCC Robocall Mitigation Database where required",
                    "Confirmed present via exact-name match against the imported RMD dataset." if rmd_status == "present" else PRESENCE_LABELS.get(rmd_status, rmd_status),
                    "RMD",
                ),
                ("Record the provider's RMD ID", rmd_record.number if rmd_record else NOT_ON_FILE, "RMD"),
                (
                    "Save evidence/date of the RMD verification",
                    f"Verified via this Compliance Suite on {today}; filing last updated {_fmt_date(rmd_record.last_updated) if rmd_record else '—'}, "
                    f"last recertified {_fmt_date(rmd_record.last_recertified) if rmd_record else '—'}.",
                    "RMD",
                ),
                ("Review the provider's RMD certification and robocall mitigation information for material concerns", _rmd_certification_summary(rmd_record), "RMD"),
                ("Confirm that the provider has not been removed or suspended from the RMD", _removal_confirmation(rmd_record, rmd_status), "RMD (flag)"),
                (
                    "Determine whether the provider uses STIR/SHAKEN and what authentication information accompanies its traffic",
                    rmd_record.implementation if rmd_record and rmd_record.implementation else NOT_ON_FILE,
                    "RMD",
                ),
            ]
        )
    )
    story.append(Spacer(1, 16))

    story.append(_section_bar("3. Know-Your-Upstream-Provider Review"))
    story.append(
        _checklist_table(
            [
                ("[FCC] Verify the provider's identity and legitimacy", _identity_legitimacy(frn_verification, rmd_status, fcc_status), "RMD / FCC"),
                (
                    "[FCC] Understand the provider's business and expected traffic relationship",
                    NOT_AVAILABLE + " — requires direct discussion with the provider.",
                    "Not on file",
                ),
                ("Identify where the provider obtains the traffic it sends", NOT_AVAILABLE + " in RMD/FCC/Registry data.", "Not on file"),
                (
                    "Identify the countries/regions from which traffic is expected",
                    NOT_AVAILABLE + " — filings record only the provider's own country, not traffic origin.",
                    "Not on file",
                ),
                ("Determine expected traffic volumes", NOT_AVAILABLE + " in RMD/FCC/Registry data.", "Not on file"),
                ("Determine expected calling patterns/use cases", NOT_AVAILABLE + " in RMD/FCC/Registry data.", "Not on file"),
                (
                    "Determine whether the provider sends traffic for its own customers or other intermediate providers",
                    _intermediate_self_report(rmd_record),
                    "RMD",
                ),
                ("Obtain a designated person who can immediately address illegal-traffic issues", _designated_contact(rmd_record), "RMD"),
                (
                    "Review any known history of illegal robocall, spoofing, traceback, or regulatory issues",
                    NOT_AVAILABLE + " — requires checking FCC enforcement/USTelecom Traceback Group records directly.",
                    "Not on file",
                ),
                ("Escalate material red flags before activating service", "; ".join(_compliance_reasons(result)) or "No material red flags identified from RMD/FCC/Registry data.", "See Sections 1-2"),
            ]
        )
    )
    story.append(Spacer(1, 16))

    story.append(_section_bar("4. Technical / Traffic Setup"))
    story.append(
        Paragraph(
            "None of these items are captured by filing data — they are this organization's own interconnection/network decisions, established directly with the provider and its technical team.",
            INTRO_STYLE,
        )
    )
    story.append(
        _checklist_table(
            [
                ("Document authorized IP addresses/interconnection points", NOT_AVAILABLE + ".", "Internal"),
                ("Establish expected traffic-volume parameters", NOT_AVAILABLE + ".", "Internal"),
                ("Establish caller-ID/ANI requirements", NOT_AVAILABLE + ".", "Internal"),
                ("Confirm this organization can identify traffic received from this provider", NOT_AVAILABLE + " — an internal network capability.", "Internal"),
                ("Confirm this organization can suspend or block the provider's traffic when required", NOT_AVAILABLE + " — an internal network capability.", "Internal"),
                (
                    "Confirm appropriate STIR/SHAKEN handling where applicable",
                    "Provider-side status is on file (Section 2); this organization's own handling is a separate internal step.",
                    "Internal",
                ),
            ]
        )
    )
    story.append(Spacer(1, 16))

    story.append(_section_bar("5. Contract and Approval"))
    story.append(
        Paragraph(
            "Most of these items are internal legal/contracting and approval steps not tracked by this Suite; agreement status is pulled from the Agreements module where available.",
            INTRO_STYLE,
        )
    )
    story.append(
        _checklist_table(
            [
                ("Execute a written agreement before traffic is accepted", _agreement_summary(agreements), "Agreements module" if agreements else "Not on file"),
                ("Include required robocall and spoofing provisions", NOT_AVAILABLE + " — internal legal/contracting step.", "Internal"),
                ("Include cooperation and traceback requirements", NOT_AVAILABLE + " — internal legal/contracting step.", "Internal"),
                ("Include suspension/blocking/termination rights", NOT_AVAILABLE + " — internal legal/contracting step.", "Internal"),
                ("Include requirement to maintain required FCC/RMD compliance", NOT_AVAILABLE + " — internal legal/contracting step.", "Internal"),
                ("Document final compliance approval", _final_approval(result), "Compliance Suite"),
                ("Record onboarding/review date", f"This report ({today}) may serve as that reference point once approved.", "Compliance Suite"),
            ]
        )
    )
    story.append(Spacer(1, 16))

    # Same "Sources Consulted" heading/position as the reference report --
    # a plain numbered list (not a checklist table), listing the real
    # internal sources this Suite actually queried for this customer. The
    # reference's own Sources Consulted also cited live web-search results
    # (company website, LinkedIn, ...); this Suite performs no such live
    # web search per customer, so only genuine internal sources are listed
    # here rather than inventing a web-research citation.
    story.append(Paragraph("Sources Consulted", SOURCES_HEADING_STYLE))
    source_items = [
        "Robocall Mitigation Database (RMD) — "
        + ("matched filing imported into this Suite." if rmd_status == "present" else PRESENCE_LABELS.get(rmd_status, rmd_status).capitalize() + "."),
        "FCC Form 499 — "
        + ("cached/live-verified filer record." if fcc_status == "present" else PRESENCE_LABELS.get(fcc_status, fcc_status).capitalize() + "."),
        "Intermediate Provider Registry — "
        + (
            "matched against the imported FCC dataset."
            if registry_record and registry_record.status == "present"
            else f"{result['intermediate_registry_status_label']}."
        ),
        "Agreements module — " + (f"{len(agreements)} agreement record(s) on file." if agreements else "no agreement records on file."),
    ]
    for index, item in enumerate(source_items, start=1):
        story.append(Paragraph(f"{index}. {item}", SOURCES_ITEM_STYLE))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=8))
    story.append(
        Paragraph(
            f"Generated by the TeleComply Compliance Suite on {today} from data already on file (RMD, FCC Form 499, Intermediate Provider "
            'Registry, and Agreements). Items marked "Not on file" or "Not available" were left unanswered rather than estimated. This '
            "document supports, but does not replace, this organization's own direct-outreach and legal/contracting steps.",
            FOOTER_STYLE,
        )
    )

    doc.build(story)
    return buffer.getvalue()
