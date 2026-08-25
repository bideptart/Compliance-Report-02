from django.urls import path

from .views import KycDocumentListCreateView, KycStatsView

urlpatterns = [
    path("documents/", KycDocumentListCreateView.as_view(), name="kyc-documents"),
    path("stats/", KycStatsView.as_view(), name="kyc-stats"),
]
