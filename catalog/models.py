import re

from django.core.exceptions import ValidationError
from django.db import models

INVENTORY_CODE_RE = re.compile(r"^[A-Za-z0-9-]{3,24}$")


def normalize_inventory_code(raw: str) -> str:
    """Trim, validate 3-24 ASCII [A-Za-z0-9-] on the trimmed input, then uppercase.

    One shared function for writes and lookups (slices 2-3 reuse it).
    """
    if not isinstance(raw, str):
        raise ValidationError("inventory_code must be 3-24 ASCII letters, digits or '-'.")
    trimmed = raw.strip()
    if not INVENTORY_CODE_RE.fullmatch(trimmed):
        raise ValidationError("inventory_code must be 3-24 ASCII letters, digits or '-'.")
    return trimmed.upper()


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)

    def __str__(self) -> str:
        return f"{self.title} — {self.author}"


class BookCopy(models.Model):
    inventory_code = models.CharField(max_length=24, unique=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="copies")

    def clean_fields(self, exclude=None) -> None:
        if isinstance(self.inventory_code, str):
            self.inventory_code = normalize_inventory_code(self.inventory_code)
        super().clean_fields(exclude=exclude)

    def clean(self) -> None:
        self.inventory_code = normalize_inventory_code(self.inventory_code)

    def __str__(self) -> str:
        return self.inventory_code
