"""Seed synthetic demo catalogue rows (slice 2: books + copies + demo users)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from catalog.models import Book, BookCopy, normalize_inventory_code

DEMO_ROWS = [
    ("Solaris", "Stanisław Lem", "LL-001"),
    ("Dune", "Frank Herbert", "LL-002"),
]

DEMO_READER = ("reader", "reader12345")
DEMO_LIBRARIAN = ("librarian", "librarian12345")


class Command(BaseCommand):
    help = "Create demo books and copies (rerunnable via get_or_create)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--extra-books",
            type=int,
            default=0,
            help="Add N synthetic books on top of the demo rows (e.g. for pagination tests).",
        )

    def handle(self, *args, **options):
        for title, author, code in DEMO_ROWS:
            self._add_book(title, author, code)
        for i in range(options["extra_books"]):
            self._add_book(f"Extra Book {i:02d}", "E2E Author", f"EX-{i:03d}")
        self._add_demo_users()
        self.stdout.write(self.style.SUCCESS("demo catalogue ready"))

    def _add_book(self, title, author, code):
        book, _ = Book.objects.get_or_create(title=title, author=author)
        BookCopy.objects.get_or_create(
            inventory_code=normalize_inventory_code(code),
            defaults={"book": book},
        )

    def _add_demo_users(self):
        group, _ = Group.objects.get_or_create(name="Librarians")
        user_model = get_user_model()
        for username, password in (DEMO_READER, DEMO_LIBRARIAN):
            user, created = user_model.objects.get_or_create(username=username)
            if created:
                user.set_password(password)
                user.save(update_fields=["password"])
        librarian = user_model.objects.get(username=DEMO_LIBRARIAN[0])
        librarian.groups.add(group)
