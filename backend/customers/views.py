from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from fcc499.models import Fcc499Filing
from rmd.models import RmdFiling
from verification.customer import (
    COMPLIANCE_STATUS_CHOICES,
    get_customer_verification,
    get_customer_verifications_bulk,
)
from verification.fcc_lookup import DEFAULT_LIVE_FETCH_BUDGET

from .models import Customer
from .serializers import CustomerSerializer

# See verification.fcc_lookup.DEFAULT_LIVE_FETCH_BUDGET -- RMD and cached FCC
# checks are single bulk queries per page (no N+1), but an uncached FCC
# company still means a real network lookup, so at most this many per
# request may trigger one live.
MAX_LIVE_FCC_LOOKUPS_PER_REQUEST = DEFAULT_LIVE_FETCH_BUDGET


class CustomerPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


def _compliance_status_param(request):
    value = (request.query_params.get("compliance_status") or "all").strip().lower()
    return value if value in COMPLIANCE_STATUS_CHOICES else "all"


def _verification_list_response(view, queryset, live_fetch_budget_for_all_mode):
    """Shared by CustomerListView and CustomerSearchView: paginate + verify.

    With no compliance_status filter (the common case), this is exactly as
    cheap as before -- paginate first, then bulk-verify only the current
    page. A compliance_status filter needs the *whole* matching queryset
    verified before it can be paginated, since the filter itself depends on
    computed fields (RMD/FCC/FRN status) that don't exist as DB columns. The
    Customers table only ever has a few hundred rows, so this is still just
    two bulk queries total -- never one query per customer, and never a live
    FCC scrape per row.
    """
    compliance_status = _compliance_status_param(view.request)

    if compliance_status == "all":
        page = view.paginate_queryset(queryset)
        objects = page if page is not None else queryset
        results = get_customer_verifications_bulk(objects, max_live_fcc_fetches=live_fetch_budget_for_all_mode)
    else:
        all_results = get_customer_verifications_bulk(list(queryset), max_live_fcc_fetches=0)
        filtered = [r for r in all_results if r["compliance"].get(compliance_status)]
        page = view.paginate_queryset(filtered)
        results = page if page is not None else filtered

    if page is not None:
        return view.get_paginated_response(results)
    return Response({"count": len(results), "next": None, "previous": None, "results": results})


class CustomerListView(generics.ListCreateAPIView):
    """GET /api/customers/?page=1&compliance_status=... - the full Customer
    Database, paginated, optionally filtered by a compliance condition.

    Every row carries the same RMD + FCC + FRN verification summary as a
    search result (see the top-level ``verification`` package). FCC checks
    are cache-only (no live scraping) to keep browsing fast; an uncached
    company shows "verification_pending" rather than blocking the page load.

    compliance_status: all (default) | fully_compliant | rmd_not_satisfied |
    no_filer_id | not_active | foreign_voice_provider -- see
    verification.customer for the exact conditions.

    POST /api/customers/ - add a new customer. Carrier name is the only
    real field on this model (see customers.models.Customer) -- Country and
    Provider are intentionally never stored here, so there's nothing else
    to collect. Duplicate carrier names (case/whitespace-insensitive, see
    normalize_carrier) are rejected with a clear validation error rather
    than a raw database integrity error.
    """

    queryset = Customer.objects.select_related("linked_rmd_record", "linked_fcc_record")
    serializer_class = CustomerSerializer
    pagination_class = CustomerPagination

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return _verification_list_response(self, queryset, live_fetch_budget_for_all_mode=0)


class CustomerSearchView(generics.ListAPIView):
    """GET /api/customers/search/?query=<carrier>&compliance_status=...

    For each matching carrier, Django (not React) uses the central
    verification service (see the top-level ``verification`` package) to:

      1. Check the RMD table for a matching company (one bulk query for the
         whole result set, not one per row).
      2. Check the FCC Form 499 cache the same way, falling back to a live
         FCC lookup for a bounded number of uncached carriers per request
         (only when compliance_status is not set -- see
         _verification_list_response).
      3. Compare the RMD FRN against the FCC CORES ID/FRN using the same
         central logic the RMD and FCC Compliance modules use.

    Only the fields needed by the frontend are returned -- never the full
    RMD or FCC datasets.
    """

    serializer_class = CustomerSerializer
    pagination_class = CustomerPagination

    def get_queryset(self):
        params = self.request.query_params
        carrier = (params.get("carrier") or params.get("search") or params.get("query") or "").strip()

        if not carrier:
            return Customer.objects.none()

        return Customer.objects.select_related("linked_rmd_record", "linked_fcc_record").filter(
            carrier__icontains=carrier
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return _verification_list_response(
            self, queryset, live_fetch_budget_for_all_mode=MAX_LIVE_FCC_LOOKUPS_PER_REQUEST
        )


class CustomerStatsView(generics.GenericAPIView):
    """GET /api/customers/stats/ - compliance breakdown across every real
    customer, for the Dashboard.

    Cache-only (no live FCC scraping), same as the Compliance Status
    dropdown filter on the Customers list -- a company whose FCC record
    hasn't been looked up yet won't count toward Fully Compliant here until
    someone searches it (see verification.fcc_lookup). Never a guess or a
    hardcoded number: computed fresh from the real Customer/RMD/FCC data
    every time this is called.
    """

    def get(self, request, *args, **kwargs):
        results = get_customer_verifications_bulk(
            Customer.objects.select_related("linked_rmd_record", "linked_fcc_record"), max_live_fcc_fetches=0
        )
        counts = {status: 0 for status in COMPLIANCE_STATUS_CHOICES if status != "all"}
        for result in results:
            for status in counts:
                if result["compliance"].get(status):
                    counts[status] += 1
        counts["total"] = len(results)
        return Response(counts)


class CustomerDetailView(generics.RetrieveAPIView):
    """GET /api/customers/<id>/?rmd_record=<id>&fcc_record=<id> - the full
    verification summary for one customer (same RMD + FCC + FRN +
    compliance shape as a list/search row).

    A single-customer lookup is cheap enough to always allow a live FCC
    fetch when the company isn't already cached -- unlike the bulk list/
    search views, there's no risk of triggering a burst of live scrapes.

    rmd_record / fcc_record (optional): when this carrier's match is
    ambiguous, the UI lets a person pick which real RMD and/or FCC record is
    actually this customer -- passing its id here pins the verification to
    that specific record (see verification.customer.get_customer_verification)
    instead of staying "Multiple Matches / Review Required" forever. An
    unknown/invalid id is ignored rather than erroring, so a stale link
    degrades to the normal ambiguous view instead of breaking the page.
    """

    queryset = Customer.objects.select_related("linked_rmd_record", "linked_fcc_record")
    serializer_class = CustomerSerializer

    def retrieve(self, request, *args, **kwargs):
        customer = self.get_object()

        rmd_record = None
        rmd_record_id = request.query_params.get("rmd_record")
        if rmd_record_id:
            rmd_record = RmdFiling.objects.filter(pk=rmd_record_id).first()

        fcc_record = None
        fcc_record_id = request.query_params.get("fcc_record")
        if fcc_record_id:
            fcc_record = Fcc499Filing.objects.filter(pk=fcc_record_id).first()

        result = get_customer_verification(
            customer, allow_live_fcc_fetch=True, rmd_record=rmd_record, fcc_record=fcc_record
        )
        # Lets the frontend tell a saved link apart from one it's only
        # previewing via ?rmd_record=/?fcc_record= (see
        # CustomerLinkRecordsView) -- e.g. to show/hide a "Save" action.
        result["linked_rmd_record_id"] = customer.linked_rmd_record_id
        result["linked_fcc_record_id"] = customer.linked_fcc_record_id
        return Response(result)


class CustomerLinkRecordsView(generics.GenericAPIView):
    """POST /api/customers/<id>/link-records/ - {"rmd_record_id": <id or
    null>, "fcc_record_id": <id or null>} (either key optional) - persists
    which real RMD and/or FCC record a person has confirmed is this
    customer, so an ambiguous match stays resolved on every future visit
    instead of only for the request that previewed it (see
    CustomerDetailView's rmd_record/fcc_record query params, and
    verification.customer.get_customer_verification's fallback to this
    saved link). Passing null for a key clears that side back to the
    plain name-based match.
    """

    queryset = Customer.objects.all()

    def post(self, request, *args, **kwargs):
        customer = self.get_object()

        if "rmd_record_id" in request.data:
            rmd_record_id = request.data.get("rmd_record_id")
            customer.linked_rmd_record = RmdFiling.objects.filter(pk=rmd_record_id).first() if rmd_record_id else None
        if "fcc_record_id" in request.data:
            fcc_record_id = request.data.get("fcc_record_id")
            customer.linked_fcc_record = (
                Fcc499Filing.objects.filter(pk=fcc_record_id).first() if fcc_record_id else None
            )
        customer.save(update_fields=["linked_rmd_record", "linked_fcc_record"])

        result = get_customer_verification(customer, allow_live_fcc_fetch=True)
        result["linked_rmd_record_id"] = customer.linked_rmd_record_id
        result["linked_fcc_record_id"] = customer.linked_fcc_record_id
        return Response(result)
