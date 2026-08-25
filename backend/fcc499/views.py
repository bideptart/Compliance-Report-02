from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from verification import rmd_lookup
from verification.fcc_lookup import compute_fcc_operational_status
from verification.fcc_lookup import verification_from_record as fcc_verification_from_record
from verification.frn import verify_frn_match

from . import lookup
from .models import Fcc499Filing
from .serializers import Fcc499DetailSerializer, Fcc499SearchResultSerializer

# RMD cross-checks are always instant local lookups (RMD is a fully
# pre-imported table), so no live-fetch budget is needed on this side --
# unlike the Customers/RMD -> FCC direction, which can trigger a live scrape.


class Fcc499Pagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


def _attach_verification(item, filing):
    rmd_verification = rmd_lookup.verification_from_name(filing.legal_name)
    fcc_verification = fcc_verification_from_record(filing)
    item["rmd_verification"] = rmd_verification
    item["frn_verification"] = verify_frn_match(rmd_verification, fcc_verification)
    item["operational_status"] = compute_fcc_operational_status(filing.registration_current_as_of)


class Fcc499SearchView(generics.ListAPIView):
    """GET /api/fcc/search/?query=<company>

    1. Search the cached FCC Form 499 records first.
    2. If nothing cached matches, run the adapted FCC lookup service once
       for that exact company name, validate/parse the result, and cache it.
    3. Cross-reference every result against the RMD table (Django-side,
       never sent to React as a bulk dataset) and attach rmd_verification,
       plus the central frn_verification result (see the top-level
       ``verification`` package) shared with the RMD and Customers modules.
    """

    serializer_class = Fcc499SearchResultSerializer
    pagination_class = Fcc499Pagination

    def list(self, request, *args, **kwargs):
        query = (request.query_params.get("query") or "").strip()

        if not query:
            return self.get_paginated_response_or_plain([], meta={"status": "ok", "message": None})

        queryset, lookup_error = lookup.search(query)
        objects = list(queryset)

        page = self.paginate_queryset(objects)
        target = page if page is not None else objects

        data = self.get_serializer(target, many=True).data
        for item, obj in zip(data, target):
            _attach_verification(item, obj)

        if page is not None:
            response = self.get_paginated_response(data)
        else:
            response = Response({"count": len(data), "next": None, "previous": None, "results": data})

        if lookup_error is not None:
            response.data["meta"] = {"status": lookup_error.status, "message": lookup_error.message}
        else:
            response.data["meta"] = {"status": "ok", "message": None}

        return response

    def get_paginated_response_or_plain(self, data, meta):
        response = Response({"count": 0, "next": None, "previous": None, "results": data})
        response.data["meta"] = meta
        return response


class Fcc499StatsView(generics.GenericAPIView):
    """GET /api/fcc/stats/ - total cached FCC Form 499 filings.

    FCC data isn't bulk-imported like RMD -- it only grows as searches cache
    real filings -- so this is a count of what's actually been looked up and
    stored so far, not a claim about the full FCC dataset."""

    def get(self, request, *args, **kwargs):
        return Response({"count": Fcc499Filing.objects.count()})


class Fcc499DetailView(generics.RetrieveAPIView):
    """GET /api/fcc/<id>/ - full stored record for one FCC Form 499 filing."""

    queryset = Fcc499Filing.objects.all()
    serializer_class = Fcc499DetailSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = self.get_serializer(instance).data
        _attach_verification(data, instance)
        return Response(data)
