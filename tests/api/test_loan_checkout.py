"""Slice 3: reader checkout by inventory_code (201 + Location)."""

import json

import pytest
from django.contrib.auth import get_user_model

from catalog.models import Book, BookCopy
from circulation.models import Loan
from tests.api.helpers import csrf_client, login


@pytest.fixture
def checkout_setup(db):
    reader = get_user_model().objects.create_user(username="reader1", password="pass12345")
    book = Book.objects.create(title="Solaris", author="Stanisław Lem")
    BookCopy.objects.create(book=book, inventory_code="LL-101")
    return reader, book


def checkout(test_client, token, payload):
    return test_client.post(
        "/api/v1/loans/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )


@pytest.mark.django_db
class TestCheckout:
    def test_reader_checks_out_copy(self, checkout_setup):
        test_client = csrf_client()
        token = login(test_client, "reader1", "pass12345")
        response = checkout(test_client, token, {"inventory_code": " ll-101 "})

        assert response.status_code == 201
        body = response.json()
        assert set(body) == {"id", "inventory_code", "book", "borrowed_at", "returned_at"}
        assert body["inventory_code"] == "LL-101"
        assert body["book"] == checkout_setup[1].pk
        assert body["returned_at"] is None
        assert response["Location"] == f"/api/v1/loans/{body['id']}/"
        assert response["Cache-Control"] == "no-store"

        loan = Loan.objects.get(pk=body["id"])
        assert loan.copy.inventory_code == "LL-101"
        assert loan.reader.username == "reader1"
        assert loan.returned_at is None

    def test_invalid_code_returns_400_without_db_write(self, checkout_setup):
        test_client = csrf_client()
        token = login(test_client, "reader1", "pass12345")
        response = checkout(test_client, token, {"inventory_code": "bad code!"})

        assert response.status_code == 400
        assert response.json()["code"] == "invalid"
        assert response["Cache-Control"] == "no-store"
        assert Loan.objects.count() == 0

    def test_missing_code_returns_400_without_db_write(self, checkout_setup):
        test_client = csrf_client()
        token = login(test_client, "reader1", "pass12345")
        response = checkout(test_client, token, {})

        assert response.status_code == 400
        assert response.json()["code"] == "invalid"
        assert Loan.objects.count() == 0

    def test_unknown_code_returns_404_without_db_write(self, checkout_setup):
        test_client = csrf_client()
        token = login(test_client, "reader1", "pass12345")
        response = checkout(test_client, token, {"inventory_code": "LL-999"})

        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
        assert Loan.objects.count() == 0

    def test_anonymous_returns_403_without_db_write(self, checkout_setup):
        test_client = csrf_client()
        token = test_client.get("/api/v1/session/").cookies["csrftoken"].value
        response = checkout(test_client, token, {"inventory_code": "LL-101"})

        assert response.status_code == 403
        assert response.json()["code"] == "forbidden"
        assert Loan.objects.count() == 0

    def test_overlong_code_returns_400_without_db_write(self, checkout_setup):
        test_client = csrf_client()
        token = login(test_client, "reader1", "pass12345")
        response = checkout(test_client, token, {"inventory_code": "A" * 25})

        assert response.status_code == 400
        assert response.json()["code"] == "invalid"
        assert response["Cache-Control"] == "no-store"
        assert Loan.objects.count() == 0

    def test_reader_without_csrf_returns_403_without_db_write(self, checkout_setup):
        test_client = csrf_client()
        login(test_client, "reader1", "pass12345")
        response = test_client.post(
            "/api/v1/loans/",
            data=json.dumps({"inventory_code": "LL-101"}),
            content_type="application/json",
        )

        assert response.status_code == 403
        assert Loan.objects.count() == 0

    def test_second_checkout_of_occupied_copy_returns_409(self, checkout_setup):
        first_client = csrf_client()
        first_token = login(first_client, "reader1", "pass12345")
        first = checkout(first_client, first_token, {"inventory_code": "LL-101"})
        assert first.status_code == 201

        get_user_model().objects.create_user(username="reader2", password="pass12345")
        second_client = csrf_client()
        second_token = login(second_client, "reader2", "pass12345")
        response = checkout(second_client, second_token, {"inventory_code": "ll-101"})

        assert response.status_code == 409
        assert response.json() == {
            "code": "copy_unavailable",
            "detail": "Copy already has an open loan.",
        }
        assert Loan.objects.filter(returned_at__isnull=True).count() == 1


@pytest.mark.django_db
def test_non_loan_paths_carry_no_no_store_header(db, client):
    books = client.get("/api/v1/books/")
    session = client.get("/api/v1/session/")
    assert books.status_code == 200
    assert session.status_code == 200
    assert "Cache-Control" not in books
    assert "Cache-Control" not in session

