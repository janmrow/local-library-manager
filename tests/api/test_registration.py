"""Slice 2, step 2: public registration with explicit CSRF, no write on refuse."""

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
        assert user.groups.filter(name="Librarians").exists() is False

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
