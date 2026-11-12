"""Slice 2, step 5: librarian-only book create, atomic, 409 rolls back."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client

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
    group, _ = Group.objects.get_or_create(name="Librarians")
    user.groups.add(group)
    return user


@pytest.mark.django_db
class TestBookCreate:
    def test_librarian_creates_book_with_first_copy(self, db):
        make_librarian()
        test_client = csrf_client()
        token = login(test_client, "lib1", "pass12345")
        response = test_client.post(
            "/api/v1/books/",
            data=json.dumps({"title": "New", "author": "Auth", "inventory_code": " ll-010 "}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "New"
        assert body["available_copies"] == 1
        assert body["total_copies"] == 1
        assert Book.objects.count() == 1
        assert BookCopy.objects.get().inventory_code == "LL-010"

    def test_duplicate_code_returns_409_without_db_write(self, db):
        book = Book.objects.create(title="Old", author="Auth")
        BookCopy.objects.create(book=book, inventory_code="LL-010")
        make_librarian()
        test_client = csrf_client()
        token = login(test_client, "lib1", "pass12345")
        response = test_client.post(
            "/api/v1/books/",
            data=json.dumps({"title": "New", "author": "Auth", "inventory_code": "ll-010"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 409
        assert response.json()["code"] == "inventory_code_taken"
        assert Book.objects.count() == 1
        assert BookCopy.objects.count() == 1

    def test_reader_returns_403_without_db_write(self, db):
        get_user_model().objects.create_user(username="reader1", password="pass12345")
        test_client = csrf_client()
        token = login(test_client, "reader1", "pass12345")
        response = test_client.post(
            "/api/v1/books/",
            data=json.dumps({"title": "New", "author": "Auth", "inventory_code": "LL-011"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 403
        assert response.json()["code"] == "forbidden"
        assert Book.objects.count() == 0
        assert BookCopy.objects.count() == 0

    def test_anonymous_returns_403_without_db_write(self, db):
        test_client = csrf_client()
        token = test_client.get("/api/v1/session/").cookies["csrftoken"].value
        response = test_client.post(
            "/api/v1/books/",
            data=json.dumps({"title": "New", "author": "Auth", "inventory_code": "LL-011"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 403
        assert Book.objects.count() == 0
        assert BookCopy.objects.count() == 0

    def test_librarian_without_csrf_returns_403_without_db_write(self, db):
        make_librarian()
        test_client = csrf_client()
        login(test_client, "lib1", "pass12345")
        response = test_client.post(
            "/api/v1/books/",
            data=json.dumps({"title": "New", "author": "Auth", "inventory_code": "LL-011"}),
            content_type="application/json",
        )
        assert response.status_code == 403
        assert Book.objects.count() == 0
        assert BookCopy.objects.count() == 0

    def test_invalid_code_returns_400_without_db_write(self, db):
        make_librarian()
        test_client = csrf_client()
        token = login(test_client, "lib1", "pass12345")
        response = test_client.post(
            "/api/v1/books/",
            data=json.dumps({"title": "New", "author": "Auth", "inventory_code": "bad code!"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid"
        assert Book.objects.count() == 0
        assert BookCopy.objects.count() == 0

    def test_create_ignores_search_query_on_response(self, db):
        make_librarian()
        test_client = csrf_client()
        token = login(test_client, "lib1", "pass12345")
        response = test_client.post(
            "/api/v1/books/?q=nothing-matching-xyz",
            data=json.dumps({"title": "New", "author": "Auth", "inventory_code": "LL-012"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "New"
        assert body["available_copies"] == 1
        assert body["total_copies"] == 1
        assert Book.objects.count() == 1
        assert BookCopy.objects.count() == 1
