"""Unit tests for inventory_code normalization (shared by writes and lookups)."""

import pytest
from django.core.exceptions import ValidationError

from catalog.models import normalize_inventory_code


def test_trims_and_uppercases():
    assert normalize_inventory_code("  ll-001 ") == "LL-001"


@pytest.mark.parametrize("raw", ["ab", "x" * 25, "LL 001", "LL_001", "ąć-123"])
def test_rejects_invalid_codes(raw):
    with pytest.raises(ValidationError):
        normalize_inventory_code(raw)


@pytest.mark.parametrize("raw", [None, 123, b"LL-001"])
def test_rejects_non_strings(raw):
    with pytest.raises(ValidationError):
        normalize_inventory_code(raw)


@pytest.mark.django_db
def test_full_clean_trims_before_max_length_check(db):
    from catalog.models import Book, BookCopy

    book = Book.objects.create(title="T", author="A")
    copy = BookCopy(inventory_code="  " + "B" * 24 + "  ", book=book)
    copy.full_clean()
    assert copy.inventory_code == "B" * 24
