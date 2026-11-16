from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model (slice 1: table only, no rows seeded)."""

    pass
