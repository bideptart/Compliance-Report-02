from django.urls import path

from .views import (
    CustomerDetailView,
    CustomerLinkRecordsView,
    CustomerListView,
    CustomerReportPDFView,
    CustomerSearchView,
    CustomerStatsView,
)

urlpatterns = [
    path("", CustomerListView.as_view(), name="customer-list"),
    path("search/", CustomerSearchView.as_view(), name="customer-search"),
    path("stats/", CustomerStatsView.as_view(), name="customer-stats"),
    path("<int:pk>/", CustomerDetailView.as_view(), name="customer-detail"),
    path("<int:pk>/link-records/", CustomerLinkRecordsView.as_view(), name="customer-link-records"),
    path("<int:pk>/report/", CustomerReportPDFView.as_view(), name="customer-report-pdf"),
]
