"""Slice 2, step 6: librarian-only copy add, 409/404/403 without writes."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client

from accounts.permissions import LIBRARIANS_GROUP
from catalog.models import Book, BookCopy


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


def make_librarian(username="lib1", password="pass12345"):
    user = get_user_model().objects.create_user(username=username, password=password)
    group, _ = Group.objects.get_or_create(name=LIBRARIANS_GROUP)
    user.groups.add(group)
    return user


@pytest.mark.django_db
class TestAddCopy:
    def test_librarian_adds_copy(self, db):
        make_librarian()
        book = Book.objects.create(title="T", author="A")
        BookCopy.objects.create(book=book, inventory_code="LL-001")
        test_client = csrf_client()
        token = login(test_client, "lib1", "pass12345")
        response = test_client.post(
            f"/api/v1/books/{book.pk}/copies/",
            data=json.dumps({"inventory_code": " ll-002 "}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 201
        body = response.json()
        copy = BookCopy.objects.get(inventory_code="LL-002")
        assert body["id"] == copy.id
        assert body["inventory_code"] == "LL-002"
        assert body["book"] == book.pk
        assert copy.book_id == book.pk
        assert BookCopy.objects.count() == 2

    def test_duplicate_code_returns_409_without_write(self, db):
        make_librarian()
        book = Book.objects.create(title="T", author="A")
        BookCopy.objects.create(book=book, inventory_code="LL-001")
        test_client = csrf_client()
        token = login(test_client, "lib1", "pass12345")
        response = test_client.post(
            f"/api/v1/books/{book.pk}/copies/",
            data=json.dumps({"inventory_code": "ll-001"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 409
        assert response.json()["code"] == "inventory_code_taken"
        assert BookCopy.objects.count() == 1

    def test_unknown_book_returns_404(self, db):
        make_librarian()
        test_client = csrf_client()
        token = login(test_client, "lib1", "pass12345")
        response = test_client.post(
            "/api/v1/books/999999/copies/",
            data=json.dumps({"inventory_code": "LL-009"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
        assert BookCopy.objects.count() == 0

    def test_reader_returns_403_without_write(self, db):
        get_user_model().objects.create_user(username="reader1", password="pass12345")
        book = Book.objects.create(title="T", author="A")
        test_client = csrf_client()
        token = login(test_client, "reader1", "pass12345")
        response = test_client.post(
            f"/api/v1/books/{book.pk}/copies/",
            data=json.dumps({"inventory_code": "LL-009"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 403
        assert BookCopy.objects.count() == 0

    def test_anonymous_returns_403_without_write(self, db):
        book = Book.objects.create(title="T", author="A")
        test_client = csrf_client()
        token = test_client.get("/api/v1/session/").cookies["csrftoken"].value
        response = test_client.post(
            f"/api/v1/books/{book.pk}/copies/",
            data=json.dumps({"inventory_code": "LL-009"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 403
        assert BookCopy.objects.count() == 0

    def test_non_post_methods_are_not_allowed(self, db):
        make_librarian()
        book = Book.objects.create(title="T", author="A")
        BookCopy.objects.create(book=book, inventory_code="LL-001")
        test_client = csrf_client()
        token = login(test_client, "lib1", "pass12345")
        get_response = test_client.get(
            f"/api/v1/books/{book.pk}/copies/", HTTP_X_CSRFTOKEN=token
        )
        assert get_response.status_code == 405
        for method in ("put", "patch", "delete"):
            response = getattr(test_client, method)(
                f"/api/v1/books/{book.pk}/copies/",
                data=json.dumps({"inventory_code": "LL-009"}),
                content_type="application/json",
                HTTP_X_CSRFTOKEN=token,
            )
            assert response.status_code == 405
        assert BookCopy.objects.count() == 1

    def test_invalid_code_returns_400_without_write(self, db):
        make_librarian()
        book = Book.objects.create(title="T", author="A")
        BookCopy.objects.create(book=book, inventory_code="LL-001")
        test_client = csrf_client()
        token = login(test_client, "lib1", "pass12345")
        response = test_client.post(
            f"/api/v1/books/{book.pk}/copies/",
            data=json.dumps({"inventory_code": "bad code!"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid"
        assert Book.objects.count() == 1
        assert BookCopy.objects.count() == 1

    def test_add_copy_ignores_search_query(self, db):
        make_librarian()
        book = Book.objects.create(title="T", author="A")
        test_client = csrf_client()
        token = login(test_client, "lib1", "pass12345")
        response = test_client.post(
            f"/api/v1/books/{book.pk}/copies/?q=nothing-matching-xyz",
            data=json.dumps({"inventory_code": "LL-009"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["inventory_code"] == "LL-009"
        assert body["book"] == book.pk
        stored = BookCopy.objects.get(inventory_code="LL-009")
        assert body["id"] == stored.id
        assert stored.book_id == book.pk
        assert BookCopy.objects.count() == 1

    def test_missing_inventory_code_returns_400_without_write(self, db):
        make_librarian()
        book = Book.objects.create(title="T", author="A")
        test_client = csrf_client()
        token = login(test_client, "lib1", "pass12345")
        response = test_client.post(
            f"/api/v1/books/{book.pk}/copies/",
            data=json.dumps({}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid"
        assert Book.objects.count() == 1
        assert BookCopy.objects.count() == 0
