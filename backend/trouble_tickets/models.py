from django.db import models

from customers.models import Customer

# New tickets always start Open; the workflow only ever moves forward
# (Open -> In Progress -> Resolved -> Closed) unless a person explicitly
# reopens one by picking an earlier status again -- nothing here enforces a
# one-way state machine, since real support work sometimes needs to step
# back (e.g. a "Resolved" ticket the customer says isn't actually fixed).
TICKET_STATUS_CHOICES = [
    ("open", "Open"),
    ("in_progress", "In Progress"),
    ("resolved", "Resolved"),
    ("closed", "Closed"),
]


def generate_ticket_number():
    """TT-000001, TT-000002, ... -- sequential and collision-safe even if a
    row was deleted in the middle (mirrors Agreement.generate_agreement_id)."""
    next_num = TroubleTicket.objects.count() + 1
    candidate = f"TT-{next_num:06d}"
    while TroubleTicket.objects.filter(ticket_number=candidate).exists():
        next_num += 1
        candidate = f"TT-{next_num:06d}"
    return candidate


class TroubleTicket(models.Model):
    """A real customer-reported issue, linked to an existing Customer (never
    a duplicated/invented name) -- one Customer can have many tickets over
    time. Nothing here is ever pre-seeded; every row reflects a ticket
    someone actually created through this module."""

    ticket_number = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="trouble_tickets")

    date_opened = models.DateField()
    problem = models.TextField()
    status = models.CharField(max_length=20, choices=TICKET_STATUS_CHOICES, default="open")

    noc_notified = models.BooleanField(default=False)
    customer_notified = models.BooleanField(default=False)

    resolution_comments = models.TextField(blank=True, null=True)
    date_closed = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = generate_ticket_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_number} - {self.customer.carrier}"
