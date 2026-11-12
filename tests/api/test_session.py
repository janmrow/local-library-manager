"""Slice 2, step 1: anonymous session state sets the CSRF cookie, no DB write."""

import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
class TestSessionState:
    def test_anonymous_get_returns_unauthenticated_and_sets_csrf_cookie(self, client, db):
        response = client.get("/api/v1/session/")
        assert response.status_code == 200
        assert response.json() == {"authenticated": False, "username": None, "is_librarian": False}
        assert "csrftoken" in response.cookies
        assert get_user_model().objects.count() == 0

    def test_authenticated_get_returns_user_state(self, client, db):
        user = get_user_model().objects.create_user(username="reader1", password="pass12345")
        client.force_login(user)
        response = client.get("/api/v1/session/")
        assert response.status_code == 200
        assert response.json() == {"authenticated": True, "username": "reader1", "is_librarian": False}
