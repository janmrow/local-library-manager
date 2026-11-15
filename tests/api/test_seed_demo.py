"""Slice 4: seed_demo is rerunnable and feeds the e2e counts."""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from accounts.permissions import LIBRARIANS_GROUP
from catalog.models import Book, BookCopy


@pytest.mark.django_db
class TestSeedDemo:
    def test_rerunnable_extra_books_counts(self, db):
        call_command("seed_demo", extra_books=5)
        assert Book.objects.count() == 2 + 5
        assert BookCopy.objects.count() == 2 + 5
        call_command("seed_demo", extra_books=5)
        assert Book.objects.count() == 2 + 5
        assert BookCopy.objects.count() == 2 + 5
        reader = get_user_model().objects.get(username="reader")
        librarian = get_user_model().objects.get(username="librarian")
        assert librarian.groups.filter(name=LIBRARIANS_GROUP).exists()
        assert not reader.groups.filter(name=LIBRARIANS_GROUP).exists()
