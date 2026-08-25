"""Dashboard-only endpoints -- everything else the Dashboard shows (the
compliance overview cards, the compliance distribution chart, the trouble
ticket overview) is served by the existing customers/stats/ and
tickets/stats/ endpoints already used elsewhere; nothing about those is
duplicated here.

This module only adds what genuinely doesn't exist anywhere else:

  * Needs Attention -- real customers with a real compliance issue, using
    the exact same verification.customer compliance logic as everything
    else (never a separate/duplicated calculation).
  * Recent Activity -- a lightweight, honest feed built directly from the
    real created_at/uploaded_at timestamps already on TroubleTicket,
    Agreement, Document, and KycDocument. No new "activity log" model or
    table was added -- there's nothing to keep in sync and nothing that
    could drift from the real data, since every row here *is* a real
    record's own creation timestamp.
"""
from datetime import timedelta

from agreements.models import Agreement
from customers.models import Customer
from django.db.models import F
from django.utils import timezone
from documents.models import Document
from kyc.models import KycDocument
from rest_framework.response import Response
from rest_framework.views import APIView
from trouble_tickets.models import TroubleTicket
from verification.customer import get_customer_verifications_bulk

from .models import ActivityFeedState

# Django sets auto_now_add and auto_now from two separate now() calls, so
# even a brand-new row's created_at and updated_at differ by a few
# microseconds -- comparing them for exact equality would misfire as a
# false "edited" event on every single creation. This threshold is how far
# apart they need to be to count as a real, later edit.
_EDIT_THRESHOLD = timedelta(seconds=5)

# Priority order for picking the single headline issue to show per row --
# a customer can genuinely fail more than one of these at once, but the
# table only has room for one Compliance Issue per row, so the most
# actionable/severe one wins. Matches the exact condition set
# verification.customer already computes -- never a separate rule.
_ISSUE_PRIORITY = [
    ("rmd_not_satisfied", "Not Present in RMD"),
    ("no_filer_id", "No Filer ID"),
    ("not_active", "Not Active"),
]


def _headline_issue(result):
    compliance = result["compliance"]
    for key, label in _ISSUE_PRIORITY:
        if compliance.get(key):
            return label
    if result["frn_verification"]["status"] != "matched":
        return "FRN Unmatched"
    if compliance.get("foreign_voice_provider"):
        return "Foreign Voice Provider"
    return None


def _yes_no(status):
    if status == "present":
        return "Yes"
    if status == "not_present":
        return "No"
    return "Review"  # multiple_matches / verification_pending / verification_error


_FRN_LABELS = {
    "matched": "Matched",
    "mismatch": "Mismatch",
    "not_available": "Unmatched",
    "verification_required": "Review",
}


class NeedsAttentionView(APIView):
    """GET /api/dashboard/needs-attention/?limit=5 - real customers that
    are not fully compliant, each with the single most relevant reason why
    (see _headline_issue), for the Dashboard's Needs Attention table.

    Cache-only (no live FCC scraping) and reuses the same bulk verification
    every other summary view uses, so these counts and the compliance
    overview cards can never disagree.
    """

    def get(self, request, *args, **kwargs):
        try:
            limit = max(1, min(int(request.query_params.get("limit", 5)), 50))
        except ValueError:
            limit = 5

        results = get_customer_verifications_bulk(
            Customer.objects.select_related("linked_rmd_record", "linked_fcc_record"), max_live_fcc_fetches=0
        )

        rows = []
        for result in results:
            if result["compliance"]["fully_compliant"]:
                continue
            issue = _headline_issue(result)
            if not issue:
                continue
            rows.append(
                {
                    "id": result["id"],
                    "company_name": result["company_name"],
                    "compliance_issue": issue,
                    "rmd_status": _yes_no(result["rmd_verification"]["status"]),
                    "fcc_status": _yes_no(result["fcc_verification"]["status"]),
                    "frn_status": _FRN_LABELS.get(result["frn_verification"]["status"], "Review"),
                }
            )

        issue_rank = {label: i for i, (_, label) in enumerate(_ISSUE_PRIORITY)}
        issue_rank["FRN Unmatched"] = len(_ISSUE_PRIORITY)
        issue_rank["Foreign Voice Provider"] = len(_ISSUE_PRIORITY) + 1
        rows.sort(key=lambda r: (issue_rank.get(r["compliance_issue"], 99), r["company_name"] or ""))

        return Response({"count": len(rows), "results": rows[:limit]})


def _activity_item(description, module, timestamp):
    return {"description": description, "module": module, "timestamp": timestamp}


class RecentActivityView(APIView):
    """GET /api/dashboard/recent-activity/?limit=8 - the most recent real
    records created across Customers, Trouble Tickets, Agreements,
    Documents, and KYC Documents, merged and sorted by their own real
    timestamp.

    Every item here is something genuinely, unambiguously true -- creation
    events (a ticket/agreement/document/customer that really was created).
    Most of these models don't track *what* changed on an edit, only
    *that* something did (a generic updated_at) -- so Trouble Tickets,
    Agreements, and KYC Documents each also surface a plain "was updated"
    event (see _EDIT_THRESHOLD) whenever updated_at is meaningfully later
    than creation, without guessing which field changed or to what. The
    Intermediate Registry is intentionally not a source here -- its status
    is a lookup against a static, manually-imported reference dataset
    (see intermediate_registry.matching), not a live re-verification with
    real drift to report on.
    """

    def get(self, request, *args, **kwargs):
        try:
            limit = max(1, min(int(request.query_params.get("limit", 8)), 50))
        except ValueError:
            limit = 8

        # A previous "Clear" only ever hides items older than the clear --
        # it can't touch the real records themselves (see ActivityFeedState
        # docstring) -- so every queryset below is filtered to strictly
        # after that cutoff before it's even fetched. Anything created
        # since then (including the very next new record) is always newer
        # than cleared_at, so it shows up automatically with no separate
        # bookkeeping.
        cleared_at = ActivityFeedState.get_cleared_at()

        items = []

        customers = Customer.objects.order_by("-imported_at")
        if cleared_at:
            customers = customers.filter(imported_at__gt=cleared_at)
        for customer in customers[:limit]:
            items.append(
                _activity_item(
                    f"Customer {customer.carrier} added",
                    "Customers",
                    customer.imported_at,
                )
            )

        tickets = TroubleTicket.objects.select_related("customer").order_by("-created_at")
        if cleared_at:
            tickets = tickets.filter(created_at__gt=cleared_at)
        for ticket in tickets[:limit]:
            items.append(
                _activity_item(
                    f"Trouble ticket {ticket.ticket_number} opened for {ticket.customer.carrier}",
                    "Trouble Tickets",
                    ticket.created_at,
                )
            )

        updated_tickets = (
            TroubleTicket.objects.select_related("customer")
            .filter(updated_at__gt=F("created_at") + _EDIT_THRESHOLD)
            .order_by("-updated_at")
        )
        if cleared_at:
            updated_tickets = updated_tickets.filter(updated_at__gt=cleared_at)
        for ticket in updated_tickets[:limit]:
            items.append(
                _activity_item(
                    f"Trouble ticket {ticket.ticket_number} updated for {ticket.customer.carrier}",
                    "Trouble Tickets",
                    ticket.updated_at,
                )
            )

        agreements = Agreement.objects.select_related("customer").order_by("-created_at")
        if cleared_at:
            agreements = agreements.filter(created_at__gt=cleared_at)
        for agreement in agreements[:limit]:
            items.append(
                _activity_item(
                    f"Agreement {agreement.agreement_id} created for {agreement.customer.carrier}",
                    "Agreements",
                    agreement.created_at,
                )
            )

        updated_agreements = (
            Agreement.objects.select_related("customer")
            .filter(updated_at__gt=F("created_at") + _EDIT_THRESHOLD)
            .order_by("-updated_at")
        )
        if cleared_at:
            updated_agreements = updated_agreements.filter(updated_at__gt=cleared_at)
        for agreement in updated_agreements[:limit]:
            items.append(
                _activity_item(
                    f"Agreement {agreement.agreement_id} updated for {agreement.customer.carrier}",
                    "Agreements",
                    agreement.updated_at,
                )
            )

        documents = Document.objects.select_related("customer").order_by("-uploaded_at")
        if cleared_at:
            documents = documents.filter(uploaded_at__gt=cleared_at)
        for document in documents[:limit]:
            module = "Tech Form" if document.document_type == "tech_form" else "Documents"
            items.append(
                _activity_item(
                    f"{'Tech form' if document.document_type == 'tech_form' else 'Document'} uploaded for {document.customer.carrier}",
                    module,
                    document.uploaded_at,
                )
            )

        kyc_documents = KycDocument.objects.select_related("customer").order_by("-uploaded_at")
        if cleared_at:
            kyc_documents = kyc_documents.filter(uploaded_at__gt=cleared_at)
        for kyc_document in kyc_documents[:limit]:
            items.append(
                _activity_item(
                    f"KYC document uploaded for {kyc_document.customer.carrier}",
                    "KYC Verification",
                    kyc_document.uploaded_at,
                )
            )

        updated_kyc_documents = (
            KycDocument.objects.select_related("customer")
            .filter(updated_at__gt=F("uploaded_at") + _EDIT_THRESHOLD)
            .order_by("-updated_at")
        )
        if cleared_at:
            updated_kyc_documents = updated_kyc_documents.filter(updated_at__gt=cleared_at)
        for kyc_document in updated_kyc_documents[:limit]:
            items.append(
                _activity_item(
                    f"KYC document updated for {kyc_document.customer.carrier}",
                    "KYC Verification",
                    kyc_document.updated_at,
                )
            )

        items.sort(key=lambda item: item["timestamp"], reverse=True)
        return Response({"results": items[:limit]})


class RecentActivityClearView(APIView):
    """POST /api/dashboard/recent-activity/clear/ - hides every current
    Recent Activity item by stamping a new ActivityFeedState.cleared_at
    (now). Never deletes or modifies any real Customer/Ticket/Agreement/
    Document/KYC/Registry record -- RecentActivityView simply stops
    showing anything timestamped at or before this moment, while anything
    that happens afterward is newer than this cutoff by construction and
    keeps appearing automatically.
    """

    def post(self, request, *args, **kwargs):
        state = ActivityFeedState.objects.create(cleared_at=timezone.now())
        return Response({"cleared_at": state.cleared_at})
