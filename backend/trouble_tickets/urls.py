from django.urls import path

from .views import TicketDetailView, TicketListCreateView, TicketStatsView

urlpatterns = [
    path("", TicketListCreateView.as_view(), name="ticket-list"),
    path("stats/", TicketStatsView.as_view(), name="ticket-stats"),
    path("<int:pk>/", TicketDetailView.as_view(), name="ticket-detail"),
]
