"""Slice 1 browse scenarios: list, search, detail, 404, derived availability."""

import pytest
from django.contrib.auth import get_user_model

from catalog.models import Book, BookCopy
from circulation.models import Loan


@pytest.fixture
def two_books(db):
    solaris = Book.objects.create(title="Solaris", author="Stanisław Lem")
    dune = Book.objects.create(title="Dune", author="Frank Herbert")
    BookCopy.objects.create(inventory_code="LL-001", book=solaris)
    BookCopy.objects.create(inventory_code="LL-002", book=dune)
    return solaris, dune


@pytest.mark.django_db
class TestBookList:
    def test_list_envelope_and_order(self, client, two_books):
        response = client.get("/api/v1/books/")
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"count", "next", "previous", "results"}
        assert body["count"] == 2
        assert [b["title"] for b in body["results"]] == ["Dune", "Solaris"]
        assert body["results"][0] == {
            "id": two_books[1].id,
            "title": "Dune",
            "author": "Frank Herbert",
            "available_copies": 1,
            "total_copies": 1,
        }

    def test_search_matches_title_or_author(self, client, two_books):
        response = client.get("/api/v1/books/", {"q": "lem"})
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert body["results"][0]["title"] == "Solaris"

    def test_search_matches_title(self, client, two_books):
        response = client.get("/api/v1/books/", {"q": "sol"})
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert body["results"][0]["title"] == "Solaris"

    def test_search_without_matches_returns_empty_list(self, client, two_books):
        response = client.get("/api/v1/books/", {"q": "zzz"})
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 0
        assert body["results"] == []

    def test_empty_query_returns_all(self, client, two_books):
        response = client.get("/api/v1/books/", {"q": ""})
        assert response.status_code == 200
        assert response.json()["count"] == 2


@pytest.mark.django_db
class TestBookDetail:
    def test_detail_shape_without_copies(self, client, two_books):
        solaris, _ = two_books
        response = client.get(f"/api/v1/books/{solaris.id}/")
        assert response.status_code == 200
        assert response.json() == {
            "id": solaris.id,
            "title": "Solaris",
            "author": "Stanisław Lem",
            "available_copies": 1,
            "total_copies": 1,
        }

    def test_unknown_id_returns_not_found_envelope(self, client, db):
        response = client.get("/api/v1/books/999999/")
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
        assert "detail" in response.json()


@pytest.mark.django_db
class TestPagination:
    def test_second_page_after_twenty(self, client, db):
        for i in range(21):
            book = Book.objects.create(title=f"Book {i:02d}", author="Author")
            BookCopy.objects.create(inventory_code=f"PP-{i:03d}", book=book)
        first = client.get("/api/v1/books/")
        assert first.status_code == 200
        assert first.json()["count"] == 21
        assert len(first.json()["results"]) == 20
        assert first.json()["next"] is not None
        assert [b["title"] for b in first.json()["results"]] == sorted(
            b["title"] for b in first.json()["results"]
        )
        second = client.get("/api/v1/books/", {"page": 2})
        assert second.status_code == 200
        assert len(second.json()["results"]) == 1
        assert second.json()["results"][0]["title"] == "Book 20"
        assert second.json()["previous"] is not None


@pytest.mark.django_db
class TestAvailability:
    def test_open_loan_reduces_available_copies(self, client, db):
        user = get_user_model().objects.create(username="reader1")
        book = Book.objects.create(title="Solaris", author="Stanisław Lem")
        copy = BookCopy.objects.create(inventory_code="LL-001", book=book)
        Loan.objects.create(copy=copy, reader=user)
        response = client.get(f"/api/v1/books/{book.id}/")
        assert response.status_code == 200
        assert response.json()["available_copies"] == 0
        assert response.json()["total_copies"] == 1

    def test_history_and_open_loan_across_copies(self, client, db):
        from django.utils import timezone

        user = get_user_model().objects.create(username="reader1")
        book = Book.objects.create(title="Solaris", author="Stanisław Lem")
        returned = BookCopy.objects.create(inventory_code="LL-001", book=book)
        open_loan = BookCopy.objects.create(inventory_code="LL-002", book=book)
        free = BookCopy.objects.create(inventory_code="LL-003", book=book)
        Loan.objects.create(copy=returned, reader=user, returned_at=timezone.now())
        Loan.objects.create(copy=open_loan, reader=user)
        expected = {"total_copies": 3, "available_copies": 2}
        detail = client.get(f"/api/v1/books/{book.id}/").json()
        assert detail["total_copies"] == expected["total_copies"]
        assert detail["available_copies"] == expected["available_copies"]
        listed = client.get("/api/v1/books/").json()["results"][0]
        assert listed["total_copies"] == expected["total_copies"]
        assert listed["available_copies"] == expected["available_copies"]


@pytest.mark.django_db
class TestApiRoot:
    def test_root_links_to_books(self, client, db):
        response = client.get("/api/v1/")
        assert response.status_code == 200
        assert response.json()["books"].endswith("/api/v1/books/")
