"""Operations normalize defensively (direct callers bypass serializers)."""

import pytest
from django.contrib.auth import get_user_model

from catalog.models import Book, BookCopy
from circulation.operations import CopyNotFound, checkout_loan


@pytest.mark.django_db
class TestCheckoutNormalize:
    def test_padded_lowercase_code_checks_out(self, db):
        reader = get_user_model().objects.create_user(username="reader1", password="pass12345")
        book = Book.objects.create(title="T", author="A")
        BookCopy.objects.create(book=book, inventory_code="LL-101")

        loan = checkout_loan(inventory_code="  ll-101  ", reader=reader)

        assert loan.copy.inventory_code == "LL-101"
        assert loan.reader == reader

    def test_invalid_code_raises_copy_not_found(self, db):
        reader = get_user_model().objects.create_user(username="reader1", password="pass12345")

        with pytest.raises(CopyNotFound):
            checkout_loan(inventory_code="bad code!", reader=reader)
