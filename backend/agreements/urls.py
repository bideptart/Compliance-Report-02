from django.urls import path

from .views import (
    AgreementDetailView,
    AgreementListCreateView,
    AgreementRenewView,
    AgreementStatsView,
    AgreementTerminateView,
)

urlpatterns = [
    path("", AgreementListCreateView.as_view(), name="agreement-list"),
    path("stats/", AgreementStatsView.as_view(), name="agreement-stats"),
    path("<int:pk>/", AgreementDetailView.as_view(), name="agreement-detail"),
    path("<int:pk>/renew/", AgreementRenewView.as_view(), name="agreement-renew"),
    path("<int:pk>/terminate/", AgreementTerminateView.as_view(), name="agreement-terminate"),
]
