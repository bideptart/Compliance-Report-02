from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from customers.models import Customer

from .models import KycDocument
from .serializers import KycDocumentSerializer


class KycPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


class KycDocumentListCreateView(generics.ListCreateAPIView):
    """GET /api/kyc/documents/?customer=<id> - every uploaded KYC document,
    newest first, optionally filtered to one customer.
    POST /api/kyc/documents/ - upload a new one (multipart: customer,
    file). Every record here is a real file someone uploaded through this
    endpoint -- nothing is pre-seeded."""

    serializer_class = KycDocumentSerializer
    pagination_class = KycPagination
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = KycDocument.objects.select_related("customer").all()
        customer_id = self.request.query_params.get("customer")
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class KycStatsView(APIView):
    """GET /api/kyc/stats/ - real counts computed from the KycDocument
    table plus the Customer table, never hardcoded:

      verified / pending / flagged -- document status counts
      not_started -- customers with zero KYC documents uploaded
    """

    def get(self, request, *args, **kwargs):
        total_customers = Customer.objects.count()
        customers_with_docs = KycDocument.objects.values("customer_id").distinct().count()

        return Response(
            {
                "verified": KycDocument.objects.filter(status="verified").count(),
                "pending": KycDocument.objects.filter(status="pending").count(),
                "flagged": KycDocument.objects.filter(status="flagged").count(),
                "not_started": total_customers - customers_with_docs,
                "total_customers": total_customers,
                "total_documents": KycDocument.objects.count(),
            }
        )
