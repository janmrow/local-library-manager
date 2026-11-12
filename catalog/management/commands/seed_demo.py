"""Seed synthetic demo catalogue rows (slice 1: books + copies only, no users)."""

from django.core.management.base import BaseCommand

from catalog.models import Book, BookCopy, normalize_inventory_code

DEMO_ROWS = [
    ("Solaris", "Stanisław Lem", "LL-001"),
    ("Dune", "Frank Herbert", "LL-002"),
]


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
        self.stdout.write(self.style.SUCCESS("demo catalogue ready"))

    def _add_book(self, title, author, code):
        book, _ = Book.objects.get_or_create(title=title, author=author)
        BookCopy.objects.get_or_create(
            inventory_code=normalize_inventory_code(code),
            defaults={"book": book},
        )
