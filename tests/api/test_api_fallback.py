"""Slice 3: unmatched API paths stay JSON 404 (no Django HTML page)."""

import json

import pytest
from django.test import Client

from tests.api.helpers import csrf_client, login, make_librarian


@pytest.mark.django_db
class TestApiFallback:
    def test_unknown_api_path_returns_json_404(self, client, db):
        response = client.get("/api/v1/loanz/")

        assert response.status_code == 404
        assert response["Content-Type"] == "application/json"
        assert response.json() == {"code": "not_found", "detail": "Not found."}

    def test_unknown_loan_subpath_post_returns_json_404(self, db):
        make_librarian()
        test_client = csrf_client()
        token = login(test_client, "lib1", "pass12345")
        response = test_client.post(
            "/api/v1/loans/1/return/extra/",
            data=json.dumps({}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        assert response.status_code == 404
        assert response.json() == {"code": "not_found", "detail": "Not found."}

    def test_unknown_api_post_without_csrf_returns_json_404(self, db):
        response = Client(enforce_csrf_checks=True).post("/api/v1/loanz/")

        assert response.status_code == 404
        assert response.json() == {"code": "not_found", "detail": "Not found."}
