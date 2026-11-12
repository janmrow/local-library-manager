"""Slice 2, step 4: sign-out clears the session, unauth DELETE is 403."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client


def csrf_client():
    return Client(enforce_csrf_checks=True)


def login(test_client, username="reader1", password="pass12345"):
    token = test_client.get("/api/v1/session/").cookies["csrftoken"].value
    response = test_client.post(
        "/api/v1/session/",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200
    return response.cookies["csrftoken"].value


@pytest.mark.django_db
class TestLogout:
    def test_logout_clears_session(self, db):
        get_user_model().objects.create_user(username="reader1", password="pass12345")
        test_client = csrf_client()
        token = login(test_client)
        response = test_client.delete("/api/v1/session/", HTTP_X_CSRFTOKEN=token)
        assert response.status_code == 204
        assert "_auth_user_id" not in test_client.session
        follow_up = test_client.get("/api/v1/session/")
        assert follow_up.json() == {"authenticated": False, "username": None, "is_librarian": False}

    def test_logout_unauthenticated_returns_403(self, db):
        test_client = csrf_client()
        token = test_client.get("/api/v1/session/").cookies["csrftoken"].value
        response = test_client.delete("/api/v1/session/", HTTP_X_CSRFTOKEN=token)
        assert response.status_code == 403
        assert response.json()["code"] == "forbidden"

    def test_logout_authenticated_without_csrf_stays_logged_in(self, db):
        get_user_model().objects.create_user(username="reader1", password="pass12345")
        test_client = csrf_client()
        login(test_client)
        response = test_client.delete("/api/v1/session/")
        assert response.status_code == 403
        assert response.json()["code"] == "forbidden"
        assert "_auth_user_id" in test_client.session
