from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model (slice 1: table only, no rows seeded)."""

    pass
