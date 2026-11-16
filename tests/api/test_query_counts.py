"""Query-count pins: catalogue and loan reads must not grow per row (no N+1)."""

import pytest
from django.contrib.auth import get_user_model

from catalog.models import Book, BookCopy
from circulation.models import Loan
from tests.api.helpers import csrf_client, login


@pytest.mark.django_db
class TestQueryCounts:
    def _seed(self, n_books=5, copies_per_book=4):
        reader = get_user_model().objects.create_user(username="reader1", password="pass12345")
        for i in range(n_books):
            book = Book.objects.create(title=f"Title {i:02d}", author="Auth")
            for j in range(copies_per_book):
                copy = BookCopy.objects.create(book=book, inventory_code=f"Q{i:02d}-{j:02d}")
                if j == 0:
                    Loan.objects.create(copy=copy, reader=reader)
        return reader

    @pytest.mark.parametrize("n_books", [3, 5])
    def test_book_list_query_count_stable(self, db, django_assert_num_queries, n_books):
        self._seed(n_books=n_books)
        test_client = csrf_client()
        login(test_client, "reader1", "pass12345")
        with django_assert_num_queries(5):
            response = test_client.get("/api/v1/books/")
        assert response.status_code == 200
        assert response.json()["count"] == n_books

    @pytest.mark.parametrize("n_books", [3, 5])
    def test_book_detail_query_count_stable(self, db, django_assert_num_queries, n_books):
        self._seed(n_books=n_books)
        book_id = Book.objects.order_by("id").first().pk
        test_client = csrf_client()
        login(test_client, "reader1", "pass12345")
        with django_assert_num_queries(4):
            response = test_client.get(f"/api/v1/books/{book_id}/")
        assert response.status_code == 200
        assert len(response.json()["available_codes"]) == 3

    @pytest.mark.parametrize("n_books", [3, 5])
    def test_loan_list_query_count_stable(self, db, django_assert_num_queries, n_books):
        self._seed(n_books=n_books)
        test_client = csrf_client()
        login(test_client, "reader1", "pass12345")
        with django_assert_num_queries(3):
            response = test_client.get("/api/v1/loans/")
        assert response.status_code == 200
        assert len(response.json()) == n_books
