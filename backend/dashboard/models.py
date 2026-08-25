from django.db import models


class ActivityFeedState(models.Model):
    """A single row recording when the Recent Activity feed was last
    cleared. Deliberately not a deletion of any real record's timestamp --
    Recent Activity is always computed live from real Customer/Ticket/
    Agreement/Document/KYC/Registry timestamps (see dashboard.views), so
    "clearing" it can't mean erasing that data. Instead this stores a
    cutoff: RecentActivityView only shows items newer than cleared_at, so
    everything before the clear disappears from the feed while every new
    event (which is always newer than any past cleared_at) keeps showing
    up automatically -- no separate "did we clear since this happened"
    bookkeeping needed anywhere else.
    """

    cleared_at = models.DateTimeField()

    @classmethod
    def get_cleared_at(cls):
        state = cls.objects.order_by("-cleared_at").first()
        return state.cleared_at if state else None
