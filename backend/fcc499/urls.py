from django.urls import path

from .views import Fcc499DetailView, Fcc499SearchView, Fcc499StatsView

urlpatterns = [
    path("search/", Fcc499SearchView.as_view(), name="fcc499-search"),
    path("stats/", Fcc499StatsView.as_view(), name="fcc499-stats"),
    path("<int:pk>/", Fcc499DetailView.as_view(), name="fcc499-detail"),
]
