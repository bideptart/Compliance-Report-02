from django.urls import path

from .views import NeedsAttentionView, RecentActivityClearView, RecentActivityView

urlpatterns = [
    path("needs-attention/", NeedsAttentionView.as_view(), name="dashboard-needs-attention"),
    path("recent-activity/", RecentActivityView.as_view(), name="dashboard-recent-activity"),
    path("recent-activity/clear/", RecentActivityClearView.as_view(), name="dashboard-recent-activity-clear"),
]
