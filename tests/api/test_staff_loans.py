"""Slice 3: librarian open-loan lookup by inventory_code."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from django.utils import timezone

from accounts.permissions import LIBRARIANS_GROUP
from catalog.models import Book, BookCopy
from circulation.models import Loan


def csrf_client():
    return Client(enforce_csrf_checks=True)


def login(test_client, username, password):
    token = test_client.get("/api/v1/session/").cookies["csrftoken"].value
    response = test_client.post(
        "/api/v1/session/",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200
    return response.cookies["csrftoken"].value


@pytest.fixture
def staff_setup(db):
    librarian = get_user_model().objects.create_user(
        username="lib1", password="pass12345"
    )
    librarian.groups.add(Group.objects.get_or_create(name=LIBRARIANS_GROUP)[0])
    reader = get_user_model().objects.create_user(
        username="reader1", password="pass12345"
    )
    book = Book.objects.create(title="Solaris", author="Stanisław Lem")
    busy = BookCopy.objects.create(book=book, inventory_code="LL-301")
    free = BookCopy.objects.create(book=book, inventory_code="LL-302")
    loan = Loan.objects.create(copy=busy, reader=reader)
    return {"loan": loan, "busy": busy, "free": free}


def staff_client():
    test_client = csrf_client()
    login(test_client, "lib1", "pass12345")
    return test_client


@pytest.mark.django_db
class TestStaffLoanLookup:
    def test_open_loan_returns_singleton_list(self, staff_setup):
        response = staff_client().get(
            "/api/v1/staff/loans/", {"inventory_code": " ll-301 "}
        )

        assert response.status_code == 200
        assert response["Cache-Control"] == "no-store"
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["id"] == staff_setup["loan"].id
        assert body[0]["inventory_code"] == "LL-301"
        assert body[0]["returned_at"] is None

    def test_free_copy_returns_empty_list(self, staff_setup):
        response = staff_client().get(
            "/api/v1/staff/loans/", {"inventory_code": "LL-302"}
        )

        assert response.status_code == 200
        assert response["Cache-Control"] == "no-store"
        assert response.json() == []

    def test_unknown_code_returns_empty_list(self, staff_setup):
        response = staff_client().get(
            "/api/v1/staff/loans/", {"inventory_code": "LL-999"}
        )

        assert response.status_code == 200
        assert response["Cache-Control"] == "no-store"
        assert response.json() == []

    def test_copy_with_only_returned_loan_returns_empty_list(self, staff_setup):
        returned_copy = BookCopy.objects.create(
            book=staff_setup["busy"].book, inventory_code="LL-303"
        )
        Loan.objects.create(
            copy=returned_copy,
            reader=get_user_model().objects.get(username="reader1"),
            returned_at=timezone.now(),
        )
        response = staff_client().get(
            "/api/v1/staff/loans/", {"inventory_code": "LL-303"}
        )

        assert response.status_code == 200
        assert response["Cache-Control"] == "no-store"
        assert response.json() == []

    @pytest.mark.parametrize(
        "params",
        [
            {},
            {"inventory_code": ""},
            {"inventory_code": "   "},
            {"inventory_code": "bad code!"},
            {"inventory_code": "A" * 25},
        ],
        ids=["missing", "empty", "whitespace", "invalid-chars", "overlong"],
    )
    def test_bad_param_returns_400(self, staff_setup, params):
        response = staff_client().get("/api/v1/staff/loans/", params)

        assert response.status_code == 400
        assert response["Cache-Control"] == "no-store"
        assert response.json()["code"] == "invalid"

    def test_repeated_param_returns_400(self, staff_setup):
        response = staff_client().get("/api/v1/staff/loans/?inventory_code=LL-301&inventory_code=LL-302")

        assert response.status_code == 400
        assert response["Cache-Control"] == "no-store"
        assert response.json()["code"] == "invalid"

    def test_reader_returns_403(self, staff_setup):
        test_client = csrf_client()
        login(test_client, "reader1", "pass12345")
        response = test_client.get(
            "/api/v1/staff/loans/", {"inventory_code": "LL-301"}
        )

        assert response.status_code == 403
        assert response["Cache-Control"] == "no-store"
        assert response.json()["code"] == "forbidden"

    def test_anonymous_returns_403(self, staff_setup):
        response = csrf_client().get(
            "/api/v1/staff/loans/", {"inventory_code": "LL-301"}
        )

        assert response.status_code == 403
        assert response["Cache-Control"] == "no-store"
        assert response.json()["code"] == "forbidden"
