"""Slice 3: idempotent librarian return (retry keeps returned_at)."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from catalog.models import Book, BookCopy
from circulation.models import Loan
from tests.api.helpers import csrf_client, login, make_librarian


@pytest.fixture
def return_setup(db):
    get_user_model().objects.create_user(username="reader1", password="pass12345")
    make_librarian()
    book = Book.objects.create(title="Solaris", author="Stanisław Lem")
    busy = BookCopy.objects.create(book=book, inventory_code="LL-401")
    old = BookCopy.objects.create(book=book, inventory_code="LL-402")
    open_loan = Loan.objects.create(
        copy=busy,
        reader=get_user_model().objects.get(username="reader1"),
    )
    returned_loan = Loan.objects.create(
        copy=old,
        reader=get_user_model().objects.get(username="reader1"),
        returned_at=timezone.now(),
    )
    return {"open": open_loan, "returned": returned_loan}


def staff_client():
    test_client = csrf_client()
    token = login(test_client, "lib1", "pass12345")
    return test_client, token


def staff_return(test_client, token, loan_id):
    return test_client.post(
        f"/api/v1/loans/{loan_id}/return/",
        data=json.dumps({}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )


@pytest.mark.django_db
class TestLoanReturn:
    def test_return_sets_returned_at(self, return_setup):
        test_client, token = staff_client()
        response = staff_return(test_client, token, return_setup["open"].id)

        assert response.status_code == 200
        assert response["Cache-Control"] == "no-store"
        body = response.json()
        assert body["id"] == return_setup["open"].id
        assert body["inventory_code"] == "LL-401"
        assert body["returned_at"] is not None
        assert Loan.objects.get(pk=return_setup["open"].id).returned_at is not None

    def test_retry_returns_same_returned_at(self, return_setup):
        test_client, token = staff_client()
        first = staff_return(test_client, token, return_setup["open"].id)
        second = staff_return(test_client, token, return_setup["open"].id)

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["returned_at"] == first.json()["returned_at"]
        assert Loan.objects.filter(returned_at__isnull=True).count() == 0

    def test_retry_of_old_loan_after_reloan_keeps_new_loan_open(self, return_setup):
        test_client, token = staff_client()
        loan_id = return_setup["open"].id
        first_return = staff_return(test_client, token, loan_id)
        old_stamp = first_return.json()["returned_at"]

        reader_client = csrf_client()
        reader_token = login(reader_client, "reader1", "pass12345")
        relona = reader_client.post(
            "/api/v1/loans/",
            data=json.dumps({"inventory_code": "LL-401"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=reader_token,
        )
        assert relona.status_code == 201

        retry = staff_return(test_client, token, loan_id)

        assert retry.status_code == 200
        assert retry.json()["returned_at"] == old_stamp
        new_loan = Loan.objects.get(pk=relona.json()["id"])
        assert new_loan.returned_at is None

    def test_return_of_already_returned_loan_keeps_stamp(self, return_setup):
        test_client, token = staff_client()
        first = staff_return(test_client, token, return_setup["returned"].id)
        second = staff_return(test_client, token, return_setup["returned"].id)

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["returned_at"] == first.json()["returned_at"]
        assert second.json()["returned_at"] is not None

    def test_return_of_missing_loan_returns_404(self, return_setup):
        test_client, token = staff_client()
        response = staff_return(test_client, token, 999999)

        assert response.status_code == 404
        assert response.json()["code"] == "not_found"

    def test_return_with_garbage_id_returns_json_404(self, return_setup):
        test_client, token = staff_client()
        response = test_client.post(
            "/api/v1/loans/abc/return/",
            data=json.dumps({}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
        assert response["Cache-Control"] == "no-store"

    def test_return_with_dotted_id_returns_json_404(self, return_setup):
        test_client, token = staff_client()
        response = test_client.post(
            "/api/v1/loans/a.b/return/",
            data=json.dumps({}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        assert response.status_code == 404
        assert response.json() == {"code": "not_found", "detail": "Loan not found."}
        assert response["Cache-Control"] == "no-store"

    def test_reader_return_returns_403_without_db_write(self, return_setup):
        test_client = csrf_client()
        token = login(test_client, "reader1", "pass12345")
        response = staff_return(test_client, token, return_setup["open"].id)

        assert response.status_code == 403
        assert response.json()["code"] == "forbidden"
        assert Loan.objects.get(pk=return_setup["open"].id).returned_at is None

    def test_anonymous_return_returns_403_without_db_write(self, return_setup):
        test_client = csrf_client()
        token = test_client.get("/api/v1/session/").cookies["csrftoken"].value
        response = staff_return(test_client, token, return_setup["open"].id)

        assert response.status_code == 403
        assert Loan.objects.get(pk=return_setup["open"].id).returned_at is None

    def test_return_without_csrf_returns_403_without_db_write(self, return_setup):
        test_client = csrf_client()
        login(test_client, "lib1", "pass12345")
        response = test_client.post(
            f"/api/v1/loans/{return_setup['open'].id}/return/",
            data=json.dumps({}),
            content_type="application/json",
        )

        assert response.status_code == 403
        assert Loan.objects.get(pk=return_setup["open"].id).returned_at is None

    def test_return_restores_available_copies(self, return_setup):
        test_client, token = staff_client()
        book_id = BookCopy.objects.get(inventory_code="LL-401").book_id
        before = test_client.get(f"/api/v1/books/{book_id}/")
        assert before.json()["available_copies"] == 1

        response = staff_return(test_client, token, return_setup["open"].id)
        assert response.status_code == 200

        after = test_client.get(f"/api/v1/books/{book_id}/")
        assert after.json()["available_copies"] == 2
        assert after.json()["total_copies"] == 2

    @pytest.mark.parametrize(
        "raw_pk",
        ["1_0", "+1", " 1 ", "１２３"],
        ids=["underscore", "plus", "padded", "fullwidth"],
    )
    def test_return_with_non_canonical_id_returns_json_404(self, return_setup, raw_pk):
        test_client, token = staff_client()
        response = test_client.post(
            f"/api/v1/loans/{raw_pk}/return/",
            data=json.dumps({}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        assert response.status_code == 404
        assert response["Cache-Control"] == "no-store"
        assert response.json() == {"code": "not_found", "detail": "Loan not found."}
