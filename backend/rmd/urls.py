from django.urls import path

from .views import (
    RmdFilingDetailView,
    RmdFilingDownloadView,
    RmdFilingListView,
    RmdFilingSearchView,
)

urlpatterns = [
    path("", RmdFilingListView.as_view(), name="rmd-list"),
    path("search/", RmdFilingSearchView.as_view(), name="rmd-search"),
    path("<int:pk>/", RmdFilingDetailView.as_view(), name="rmd-detail"),
    path("<int:pk>/download/", RmdFilingDownloadView.as_view(), name="rmd-download"),
]
