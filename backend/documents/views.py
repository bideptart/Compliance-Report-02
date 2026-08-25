from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from customers.models import Customer

from .models import Document
from .serializers import DocumentSerializer


class DocumentPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


class DocumentListCreateView(APIView):
    """GET /api/documents/ - every uploaded document, newest first.

    POST /api/documents/ - upload one or more files in a single request
    (multipart: customer, files -- repeat the "files" field for each
    file). One Document row is created per file, all sharing the same
    customer, so a multi-file upload always shows up as that many real
    rows in the library, never merged or dropped.
    """

    parser_classes = [MultiPartParser, FormParser]
    pagination_class = DocumentPagination

    def get(self, request, *args, **kwargs):
        queryset = Document.objects.select_related("customer").all()

        customer_id = request.query_params.get("customer")
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        document_type = request.query_params.get("document_type")
        if document_type:
            queryset = queryset.filter(document_type=document_type)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = DocumentSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, *args, **kwargs):
        customer_id = request.data.get("customer")
        files = request.FILES.getlist("files")
        document_type = request.data.get("document_type") or "document"

        if not customer_id:
            return Response({"customer": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
        if not files:
            return Response({"files": ["At least one file is required."]}, status=status.HTTP_400_BAD_REQUEST)

        try:
            customer = Customer.objects.get(pk=customer_id)
        except (Customer.DoesNotExist, ValueError):
            return Response({"customer": ["Customer not found."]}, status=status.HTTP_400_BAD_REQUEST)

        created = []
        for f in files:
            serializer = DocumentSerializer(
                data={"customer": customer.id, "file": f, "document_type": document_type},
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            created.append(serializer.data)

        return Response(created, status=status.HTTP_201_CREATED)
