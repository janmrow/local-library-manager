"""Slice 2, step 3: sign-in with CSRF, session cookie, CSRF rotation."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client


def csrf_client():
    return Client(enforce_csrf_checks=True)


def get_token(test_client):
    response = test_client.get("/api/v1/session/")
    assert response.status_code == 200
    return response.cookies["csrftoken"].value


@pytest.mark.django_db
class TestLogin:
    def test_librarian_login_returns_is_librarian_true(self, db):
        from django.contrib.auth.models import Group

        from accounts.permissions import LIBRARIANS_GROUP

        user = get_user_model().objects.create_user(username="lib1", password="pass12345")
        group, _ = Group.objects.get_or_create(name=LIBRARIANS_GROUP)
        user.groups.add(group)
        test_client = csrf_client()
        token = get_token(test_client)
        response = test_client.post(
            "/api/v1/session/",
            data=json.dumps({"username": "lib1", "password": "pass12345"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 200
        assert response.json() == {"authenticated": True, "username": "lib1", "is_librarian": True}

    def test_login_success_sets_session_and_rotates_csrf(self, db):
        get_user_model().objects.create_user(username="reader1", password="pass12345")
        test_client = csrf_client()
        first_token = get_token(test_client)
        response = test_client.post(
            "/api/v1/session/",
            data=json.dumps({"username": "reader1", "password": "pass12345"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=first_token,
        )
        assert response.status_code == 200
        assert response.json() == {
            "authenticated": True,
            "username": "reader1",
            "is_librarian": False,
        }
        assert "sessionid" in response.cookies
        second_token = response.cookies["csrftoken"].value
        assert second_token != first_token
        follow_up = test_client.get("/api/v1/session/")
        assert follow_up.json()["authenticated"] is True

    def test_login_wrong_password_returns_400_without_session(self, db):
        get_user_model().objects.create_user(username="reader1", password="pass12345")
        test_client = csrf_client()
        token = get_token(test_client)
        response = test_client.post(
            "/api/v1/session/",
            data=json.dumps({"username": "reader1", "password": "wrong12345"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid"
        assert "_auth_user_id" not in test_client.session

    def test_login_without_csrf_returns_403_without_session(self, db):
        get_user_model().objects.create_user(username="reader1", password="pass12345")
        test_client = csrf_client()
        test_client.get("/api/v1/session/")
        response = test_client.post(
            "/api/v1/session/",
            data=json.dumps({"username": "reader1", "password": "pass12345"}),
            content_type="application/json",
        )
        assert response.status_code == 403
        assert response.json()["code"] == "forbidden"
        assert "_auth_user_id" not in test_client.session

    def test_login_missing_fields_returns_400(self, db):
        test_client = csrf_client()
        token = get_token(test_client)
        response = test_client.post(
            "/api/v1/session/",
            data=json.dumps({"username": "reader1"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid"

    def test_login_non_object_body_returns_400_envelope(self, db):
        test_client = csrf_client()
        token = get_token(test_client)
        response = test_client.post(
            "/api/v1/session/",
            data=json.dumps([]),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid"
