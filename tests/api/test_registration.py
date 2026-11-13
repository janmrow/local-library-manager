"""Slice 2, step 2: public registration with explicit CSRF, no write on refuse."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from accounts.permissions import LIBRARIANS_GROUP


def csrf_client():
    return Client(enforce_csrf_checks=True)


def get_token(test_client):
    response = test_client.get("/api/v1/session/")
    assert response.status_code == 200
    return response.cookies["csrftoken"].value


@pytest.mark.django_db
class TestRegistration:
    def test_register_creates_reader_with_csrf(self, db):
        test_client = csrf_client()
        token = get_token(test_client)
        response = test_client.post(
            "/api/v1/accounts/",
            data=json.dumps({"username": "reader1", "password": "pass12345"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["username"] == "reader1"
        assert "password" not in body
        user = get_user_model().objects.get(username="reader1")
        assert user.check_password("pass12345")
        assert user.groups.filter(name=LIBRARIANS_GROUP).exists() is False

    def test_register_without_csrf_returns_403_without_db_write(self, db):
        test_client = csrf_client()
        test_client.get("/api/v1/session/")
        response = test_client.post(
            "/api/v1/accounts/",
            data=json.dumps({"username": "reader1", "password": "pass12345"}),
            content_type="application/json",
        )
        assert response.status_code == 403
        assert response.json()["code"] == "forbidden"
        assert get_user_model().objects.count() == 0

    def test_duplicate_username_returns_400(self, db):
        get_user_model().objects.create_user(username="reader1", password="pass12345")
        test_client = csrf_client()
        token = get_token(test_client)
        response = test_client.post(
            "/api/v1/accounts/",
            data=json.dumps({"username": "reader1", "password": "other12345"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid"
        assert get_user_model().objects.count() == 1

    def test_missing_password_returns_400_envelope(self, db):
        test_client = csrf_client()
        token = get_token(test_client)
        response = test_client.post(
            "/api/v1/accounts/",
            data=json.dumps({"username": "reader1"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid"
        assert get_user_model().objects.count() == 0

    def test_privilege_fields_are_ignored(self, db):
        from django.contrib.auth.models import Group, Permission

        group, _ = Group.objects.get_or_create(name=LIBRARIANS_GROUP)
        perm = Permission.objects.filter(codename="add_book").first()
        payload = {
            "username": "reader1",
            "password": "pass12345",
            "is_staff": True,
            "is_superuser": True,
            "groups": [group.id],
        }
        if perm is not None:
            payload["user_permissions"] = [perm.id]
        test_client = csrf_client()
        token = get_token(test_client)
        response = test_client.post(
            "/api/v1/accounts/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 201
        user = get_user_model().objects.get(username="reader1")
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.groups.exists() is False
        assert user.get_all_permissions() == set()

    def test_non_object_body_returns_400_without_db_write(self, db):
        test_client = csrf_client()
        token = get_token(test_client)
        response = test_client.post(
            "/api/v1/accounts/",
            data=json.dumps([]),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid"
        assert get_user_model().objects.count() == 0

    def test_registration_does_not_log_in(self, db):
        test_client = csrf_client()
        token = get_token(test_client)
        response = test_client.post(
            "/api/v1/accounts/",
            data=json.dumps({"username": "reader1", "password": "pass12345"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 201
        state = test_client.get("/api/v1/session/")
        assert state.json() == {"authenticated": False, "username": None, "is_librarian": False}

    def test_password_with_surrounding_spaces_round_trips(self, db):
        test_client = csrf_client()
        token = get_token(test_client)
        response = test_client.post(
            "/api/v1/accounts/",
            data=json.dumps({"username": "reader1", "password": "  pass12345  "}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 201
        user = get_user_model().objects.get(username="reader1")
        assert user.check_password("  pass12345  ") is True
        assert user.check_password("pass12345") is False
        login_token = test_client.get("/api/v1/session/").cookies["csrftoken"].value
        login_response = test_client.post(
            "/api/v1/session/",
            data=json.dumps({"username": "reader1", "password": "  pass12345  "}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=login_token,
        )
        assert login_response.status_code == 200
        assert login_response.json()["authenticated"] is True
