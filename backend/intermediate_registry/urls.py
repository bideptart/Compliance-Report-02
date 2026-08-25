from django.urls import path

from .views import (
    RegistryCheckNowView,
    RegistryDetailView,
    RegistryEscalationCreateView,
    RegistryEscalationDetailView,
    RegistryListView,
    RegistryStatsView,
)

urlpatterns = [
    path("", RegistryListView.as_view(), name="registry-list"),
    path("stats/", RegistryStatsView.as_view(), name="registry-stats"),
    path("<int:pk>/", RegistryDetailView.as_view(), name="registry-detail"),
    path("<int:pk>/check/", RegistryCheckNowView.as_view(), name="registry-check-now"),
    path("<int:record_id>/escalations/", RegistryEscalationCreateView.as_view(), name="registry-escalation-create"),
    path("escalations/<int:pk>/", RegistryEscalationDetailView.as_view(), name="registry-escalation-detail"),
]
