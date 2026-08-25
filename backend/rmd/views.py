from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from verification import fcc_lookup, rmd_lookup
from verification.frn import verify_frn_match

from .models import RmdFiling
from .official_pdf import OfficialPdfError, fetch_official_pdf
from .serializers import (
    RmdFilingDetailSerializer,
    RmdFilingListSerializer,
    RmdSearchResultSerializer,
)

# A deliberate, narrow company-name search (unlike the Customers module's
# broad list/browse view) realistically returns a handful of RMD records for
# a handful of distinct real companies, so it's worth checking every row
# against a real, live FCC search rather than leaving later rows sitting at
# "verification_pending" just because they came after row 3 -- one page's
# worth (RmdPagination.page_size below) is a generous, still-bounded cap.
MAX_LIVE_FCC_LOOKUPS_PER_REQUEST = 25


class RmdPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


class RmdFilingListView(generics.ListAPIView):
    """GET /api/rmd/ - paginated listing of all imported RMD records."""

    queryset = RmdFiling.objects.all()
    serializer_class = RmdFilingListSerializer
    pagination_class = RmdPagination


class RmdFilingSearchView(generics.ListAPIView):
    """GET /api/rmd/search/ - search by business/company name, FRN, or OCN.

    Accepts ``company``, ``frn``, and ``ocn`` (each optional, combined with
    AND when more than one is given), plus a legacy free-text ``query`` for
    backward compatibility. Returns nothing unless at least one search term
    is supplied -- the full dataset is never dumped to the client.

    Each result also carries the same FCC cross-check and central
    frn_verification result (see the top-level ``verification`` package)
    used by the FCC Compliance and Customers modules, so all three modules
    agree on the same company's FRN match status.

    Note: the source RMD CSV has no dedicated OCN column, so ``ocn`` is
    matched against the FRN-related fields (``frn`` / ``other_frns``) rather
    than a fabricated OCN field.
    """

    serializer_class = RmdSearchResultSerializer
    pagination_class = RmdPagination

    def get_queryset(self):
        params = self.request.query_params
        company = params.get("company", "").strip()
        frn = params.get("frn", "").strip()
        ocn = params.get("ocn", "").strip()
        legacy_query = params.get("query", "").strip()

        if not (company or frn or ocn or legacy_query):
            return RmdFiling.objects.none()

        queryset = RmdFiling.objects.all()

        if company:
            queryset = queryset.filter(business_name__icontains=company)

        if frn:
            queryset = queryset.filter(Q(frn__icontains=frn) | Q(other_frns__icontains=frn))

        if ocn:
            queryset = queryset.filter(Q(frn__icontains=ocn) | Q(other_frns__icontains=ocn))

        if legacy_query and not (company or frn or ocn):
            queryset = queryset.filter(
                Q(business_name__icontains=legacy_query)
                | Q(frn__icontains=legacy_query)
                | Q(number__icontains=legacy_query)
                | Q(other_frns__icontains=legacy_query)
                | Q(other_dba_names__icontains=legacy_query)
            )

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        objects = page if page is not None else queryset

        data = self.get_serializer(objects, many=True).data
        for index, (item, obj) in enumerate(zip(data, objects)):
            rmd_verification = rmd_lookup.verification_from_record(obj)
            fcc_verification = fcc_lookup.verification_from_name(
                obj.business_name, allow_live_fetch=index < MAX_LIVE_FCC_LOOKUPS_PER_REQUEST
            )
            item["fcc_verification"] = fcc_verification
            item["frn_verification"] = verify_frn_match(rmd_verification, fcc_verification)

        if page is not None:
            return self.get_paginated_response(data)
        return Response({"count": len(data), "next": None, "previous": None, "results": data})


class RmdFilingDetailView(generics.RetrieveAPIView):
    """GET /api/rmd/<id>/ - full detail for a single RMD record."""

    queryset = RmdFiling.objects.all()
    serializer_class = RmdFilingDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = self.get_serializer(instance).data
        rmd_verification = rmd_lookup.verification_from_record(instance)
        fcc_verification = fcc_lookup.verification_from_name(instance.business_name, allow_live_fetch=True)
        data["fcc_verification"] = fcc_verification
        data["frn_verification"] = verify_frn_match(rmd_verification, fcc_verification)
        return Response(data)


class RmdFilingDownloadView(APIView):
    """GET /api/rmd/<id>/download/ - the real, official filing PDF fetched
    live from the FCC's own RMD portal (see rmd.official_pdf), keyed off
    this record's sys_id. Never a locally-generated approximation -- if the
    live fetch fails or no filing PDF exists for this record, this returns
    a real error rather than a fabricated substitute.
    """

    def get(self, request, pk, *args, **kwargs):
        record = get_object_or_404(RmdFiling, pk=pk)

        try:
            pdf_bytes, source_filename = fetch_official_pdf(record.sys_id)
        except OfficialPdfError as exc:
            status_code = 404 if exc.status == "not_found" else 502
            return Response({"detail": exc.message}, status=status_code)

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{source_filename}"'
        return response
