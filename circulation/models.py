from django.conf import settings
from django.db import models
from django.db.models import Q


class Loan(models.Model):
    """Loan table ships in slice 1 (DDL only); writes arrive in slice 3."""

    copy = models.ForeignKey("catalog.BookCopy", on_delete=models.CASCADE)
    reader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    borrowed_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["copy"],
                condition=Q(returned_at__isnull=True),
                name="unique_open_loan_per_copy",
            )
        ]
