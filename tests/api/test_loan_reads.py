"""Slice 3: loan reads scoped to the caller (foreign id -> 404)."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from catalog.models import Book, BookCopy
from circulation.models import Loan
from tests.api.helpers import csrf_client, login, make_librarian


@pytest.fixture
def loan_setup(db):
    users = get_user_model()
    reader1 = users.objects.create_user(username="reader1", password="pass12345")
    reader2 = users.objects.create_user(username="reader2", password="pass12345")
    book = Book.objects.create(title="Solaris", author="Stanisław Lem")
    open1 = BookCopy.objects.create(book=book, inventory_code="LL-201")
    open2 = BookCopy.objects.create(book=book, inventory_code="LL-202")
    old = BookCopy.objects.create(book=book, inventory_code="LL-203")
    old2 = BookCopy.objects.create(book=book, inventory_code="LL-204")
    loan1 = Loan.objects.create(copy=open1, reader=reader1)
    loan2 = Loan.objects.create(copy=open2, reader=reader2)
    returned = Loan.objects.create(
        copy=old, reader=reader1, returned_at=timezone.now()
    )
    returned2 = Loan.objects.create(
        copy=old2, reader=reader2, returned_at=timezone.now()
    )
    return {"loan1": loan1, "loan2": loan2, "returned": returned, "returned2": returned2}


def authed_client(username):
    test_client = csrf_client()
    login(test_client, username, "pass12345")
    return test_client


@pytest.mark.django_db
class TestLoanReads:
    def test_list_shows_only_own_open_loans(self, loan_setup):
        test_client = authed_client("reader1")
        response = test_client.get("/api/v1/loans/")

        assert response.status_code == 200
        assert response["Cache-Control"] == "no-store"
        body = response.json()
        assert isinstance(body, list)
        assert [loan["id"] for loan in body] == [loan_setup["loan1"].id]
        assert body[0]["inventory_code"] == "LL-201"
        assert body[0]["returned_at"] is None

    def test_detail_returns_own_open_loan(self, loan_setup):
        test_client = authed_client("reader1")
        response = test_client.get(f"/api/v1/loans/{loan_setup['loan1'].id}/")

        assert response.status_code == 200
        assert response["Cache-Control"] == "no-store"
        assert response.json()["inventory_code"] == "LL-201"

    def test_detail_returns_own_returned_loan(self, loan_setup):
        test_client = authed_client("reader1")
        response = test_client.get(f"/api/v1/loans/{loan_setup['returned'].id}/")

        assert response.status_code == 200
        assert response["Cache-Control"] == "no-store"
        assert response.json()["inventory_code"] == "LL-203"
        assert response.json()["returned_at"] is not None

    def test_detail_of_other_readers_loan_returns_404(self, loan_setup):
        test_client = authed_client("reader1")
        response = test_client.get(f"/api/v1/loans/{loan_setup['loan2'].id}/")

        assert response.status_code == 404
        assert response["Cache-Control"] == "no-store"
        assert response.json() == {"code": "not_found", "detail": "Loan not found."}

    def test_detail_of_other_readers_returned_loan_returns_404(self, loan_setup):
        test_client = authed_client("reader1")
        response = test_client.get(f"/api/v1/loans/{loan_setup['returned2'].id}/")

        assert response.status_code == 404
        assert response["Cache-Control"] == "no-store"
        assert response.json() == {"code": "not_found", "detail": "Loan not found."}

    def test_detail_of_missing_loan_returns_404(self, loan_setup):
        test_client = authed_client("reader1")
        response = test_client.get("/api/v1/loans/999999/")

        assert response.status_code == 404
        assert response["Cache-Control"] == "no-store"
        assert response.json() == {"code": "not_found", "detail": "Loan not found."}

    def test_detail_of_non_integer_pk_returns_json_404(self, loan_setup):
        test_client = authed_client("reader1")
        response = test_client.get("/api/v1/loans/abc/")

        assert response.status_code == 404
        assert response.json() == {"code": "not_found", "detail": "Loan not found."}
        assert response["Cache-Control"] == "no-store"

    def test_detail_of_dotted_pk_returns_json_404(self, loan_setup):
        test_client = authed_client("reader1")
        response = test_client.get("/api/v1/loans/a.b/")

        assert response.status_code == 404
        assert response.json() == {"code": "not_found", "detail": "Loan not found."}
        assert response["Cache-Control"] == "no-store"

    def test_anonymous_list_returns_403(self, loan_setup):
        test_client = csrf_client()
        response = test_client.get("/api/v1/loans/")

        assert response.status_code == 403
        assert response["Cache-Control"] == "no-store"
        assert response.json()["code"] == "forbidden"

    def test_anonymous_detail_returns_403(self, loan_setup):
        test_client = csrf_client()
        response = test_client.get(f"/api/v1/loans/{loan_setup['loan1'].id}/")

        assert response.status_code == 403
        assert response["Cache-Control"] == "no-store"
        assert response.json()["code"] == "forbidden"

    def test_anonymous_detail_of_missing_loan_returns_403(self, loan_setup):
        # Auth runs before scope and before existence: anonymous gets 403
        # (not 404) even for an id that belongs to nobody, so loan
        # existence is never revealed to an unauthenticated caller.
        test_client = csrf_client()
        response = test_client.get("/api/v1/loans/999999/")

        assert response.status_code == 403
        assert response["Cache-Control"] == "no-store"
        assert response.json()["code"] == "forbidden"

    def test_list_orders_open_loans_by_borrowed_then_id(self, db):
        from datetime import timedelta

        reader = get_user_model().objects.create_user(
            username="reader1", password="pass12345"
        )
        book = Book.objects.create(title="Solaris", author="Stanisław Lem")
        first_copy = BookCopy.objects.create(book=book, inventory_code="LL-201")
        second_copy = BookCopy.objects.create(book=book, inventory_code="LL-202")
        first = Loan.objects.create(copy=first_copy, reader=reader)
        second = Loan.objects.create(copy=second_copy, reader=reader)
        # Reverse borrowed_at vs id order: without order_by the DB would
        # return insertion order [first, second]; the contract is borrowed,id.
        Loan.objects.filter(pk=first.pk).update(
            borrowed_at=timezone.now() + timedelta(days=1)
        )
        Loan.objects.filter(pk=second.pk).update(
            borrowed_at=timezone.now() - timedelta(days=1)
        )

        test_client = authed_client("reader1")
        response = test_client.get("/api/v1/loans/")

        assert response.status_code == 200
        assert [loan["id"] for loan in response.json()] == [second.id, first.id]

    def test_unsupported_methods_return_405_envelope(self, loan_setup):
        test_client = csrf_client()
        token = login(test_client, "reader1", "pass12345")
        for method, url in (
            ("put", "/api/v1/loans/"),
            ("delete", f"/api/v1/loans/{loan_setup['loan1'].id}/"),
        ):
            response = getattr(test_client, method)(
                url, HTTP_X_CSRFTOKEN=token
            )

            assert response.status_code == 405
            assert response["Cache-Control"] == "no-store"
            assert response.json()["code"] == "method_not_allowed"

        make_librarian()
        staff_client = csrf_client()
        login(staff_client, "lib1", "pass12345")
        response = staff_client.get(f"/api/v1/loans/{loan_setup['loan1'].id}/return/")

        assert response.status_code == 405
        assert response["Cache-Control"] == "no-store"
        assert response.json()["code"] == "method_not_allowed"
