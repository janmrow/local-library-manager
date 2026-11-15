"""Slice 4 observability: X-Request-ID is generated, propagated, and logged."""

import json
import logging
import re
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings

from catalog.models import Book, BookCopy
from circulation.models import Loan
from config.middleware import RequestIdMiddleware
from tests.api.helpers import csrf_client, login


def _request_lines(caplog):
    return [r for r in caplog.records if r.name == "config.middleware"]


@pytest.mark.django_db
class TestRequestId:
    def test_generates_id_when_absent(self, client, caplog, db):
        BookCopy.objects.create(
            book=Book.objects.create(title="Solaris", author="Stanisław Lem"),
            inventory_code="LL-001",
        )
        with caplog.at_level(logging.INFO, logger="config.middleware"):
            response = client.get("/api/v1/books/")
        assert response.status_code == 200
        generated = response.headers.get("X-Request-ID")
        assert generated
        assert uuid.UUID(generated).version == 4
        records = _request_lines(caplog)
        assert records, "expected one request log line"
        line = records[-1].getMessage()
        assert "GET" in line and "/api/v1/books/" in line and "200" in line
        assert generated in line
        assert re.search(r"\d+(\.\d+)?ms", line)

    def test_propagates_incoming_id(self, client, caplog, db):
        with caplog.at_level(logging.INFO, logger="config.middleware"):
            response = client.get("/api/v1/books/", HTTP_X_REQUEST_ID="diag-123")
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == "diag-123"
        line = _request_lines(caplog)[-1].getMessage()
        assert "diag-123" in line

    def test_blank_header_generates_new_id(self, client, db):
        response = client.get("/api/v1/books/", HTTP_X_REQUEST_ID="   ")
        assert response.status_code == 200
        generated = response.headers.get("X-Request-ID")
        assert generated and generated.strip()
        assert uuid.UUID(generated).version == 4

    @pytest.mark.parametrize(
        "bad_id", ["has space", "semi;colon", "a\nforged", "x" * 65, "x" * 5000]
    )
    def test_invalid_id_is_replaced_not_echoed(self, client, bad_id, db):
        response = client.get("/api/v1/books/", HTTP_X_REQUEST_ID=bad_id)
        assert response.status_code == 200
        echoed = response.headers.get("X-Request-ID")
        assert echoed != bad_id
        assert uuid.UUID(echoed).version == 4

    def test_error_responses_carry_the_id_and_log_line(self, client, caplog, db):
        with caplog.at_level(logging.INFO, logger="config.middleware"):
            response = client.get("/api/v1/books/999999/", HTTP_X_REQUEST_ID="diag-404")
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
        assert response.headers.get("X-Request-ID") == "diag-404"
        line = _request_lines(caplog)[-1].getMessage()
        assert "GET" in line and "/api/v1/books/999999/" in line and "404" in line
        assert "diag-404" in line

    def test_unmatched_api_path_carries_the_id(self, client, caplog, db):
        with caplog.at_level(logging.INFO, logger="config.middleware"):
            response = client.get("/api/v1/does-not-exist/", HTTP_X_REQUEST_ID="diag-404")
        assert response.status_code == 404
        assert response.json() == {"code": "not_found", "detail": "Not found."}
        assert response.headers.get("X-Request-ID") == "diag-404"
        line = _request_lines(caplog)[-1].getMessage()
        assert "diag-404" in line and "404" in line

    def test_exception_path_still_logs_request_id(self, rf, caplog):
        def boom(request):
            raise RuntimeError("boom")

        middleware = RequestIdMiddleware(boom)
        request = rf.get("/api/v1/books/", HTTP_X_REQUEST_ID="diag-500")
        with caplog.at_level(logging.INFO, logger="config.middleware"):
            with pytest.raises(RuntimeError, match="boom"):
                middleware(request)
        records = _request_lines(caplog)
        assert records, "expected a log line even when the view crashes"
        line = records[-1].getMessage()
        assert "GET" in line and "/api/v1/books/" in line and "500" in line
        assert "diag-500" in line


@pytest.mark.django_db
class TestRequestIdOnErrorEnvelopes:
    """The envelopes diagnosis needs (400/403/409) keep the request ID."""

    @pytest.fixture
    def reader_client(self, db):
        get_user_model().objects.create_user(username="reader1", password="pass12345")
        test_client = csrf_client()
        token = login(test_client, "reader1", "pass12345")
        return test_client, token

    @staticmethod
    def _assert_logged(caplog, rid, method, path, status):
        records = [
            r
            for r in caplog.records
            if r.name == "config.middleware" and rid in r.getMessage()
        ]
        assert records, f"no log line for rid={rid}"
        line = records[-1].getMessage()
        assert method in line and path in line and str(status) in line

    def _post_loan(self, test_client, token, rid, payload):
        return test_client.post(
            "/api/v1/loans/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_X_REQUEST_ID=rid,
        )

    def test_400_carries_id(self, caplog, reader_client):
        test_client, token = reader_client
        with caplog.at_level(logging.INFO, logger="config.middleware"):
            response = self._post_loan(
                test_client, token, "diag-400", {"inventory_code": "bad code!"}
            )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid"
        assert response.headers.get("X-Request-ID") == "diag-400"
        self._assert_logged(caplog, "diag-400", "POST", "/api/v1/loans/", 400)

    def test_403_csrf_carries_id(self, caplog, db):
        test_client = csrf_client()
        with caplog.at_level(logging.INFO, logger="config.middleware"):
            response = test_client.post(
                "/api/v1/loans/",
                data=json.dumps({"inventory_code": "LL-001"}),
                content_type="application/json",
                HTTP_X_REQUEST_ID="diag-403",
            )
        assert response.status_code == 403
        assert response.headers.get("X-Request-ID") == "diag-403"
        self._assert_logged(caplog, "diag-403", "POST", "/api/v1/loans/", 403)

    def test_403_permission_carries_id(self, caplog, reader_client, db):
        test_client, token = reader_client
        reader = get_user_model().objects.get(username="reader1")
        book = Book.objects.create(title="Solaris", author="Stanisław Lem")
        copy = BookCopy.objects.create(book=book, inventory_code="LL-501")
        loan = Loan.objects.create(copy=copy, reader=reader)
        with caplog.at_level(logging.INFO, logger="config.middleware"):
            response = test_client.post(
                f"/api/v1/loans/{loan.id}/return/",
                HTTP_X_CSRFTOKEN=token,
                HTTP_X_REQUEST_ID="diag-403",
            )
        assert response.status_code == 403
        assert response.headers.get("X-Request-ID") == "diag-403"
        self._assert_logged(
            caplog, "diag-403", "POST", f"/api/v1/loans/{loan.id}/return/", 403
        )

    def test_409_carries_id(self, caplog, reader_client, db):
        test_client, token = reader_client
        book = Book.objects.create(title="Solaris", author="Stanisław Lem")
        BookCopy.objects.create(book=book, inventory_code="LL-502")
        with caplog.at_level(logging.INFO, logger="config.middleware"):
            first = self._post_loan(
                test_client, token, "diag-201", {"inventory_code": "LL-502"}
            )
            second = self._post_loan(
                test_client, token, "diag-409", {"inventory_code": "LL-502"}
            )
        assert first.status_code == 201
        assert second.status_code == 409
        assert second.json()["code"] == "copy_unavailable"
        assert second.headers.get("X-Request-ID") == "diag-409"
        self._assert_logged(caplog, "diag-409", "POST", "/api/v1/loans/", 409)


class TestCrashResponseKeepsHeader:
    """A real crash still returns a response through this middleware, so the
    500 carries the header and the log line stays the correlation point."""

    def test_crash_response_keeps_header_and_log_has_rid(self, caplog):
        plain = Client(enforce_csrf_checks=False, raise_request_exception=False)
        with caplog.at_level(logging.INFO, logger="config.middleware"):
            with override_settings(
                ROOT_URLCONF="tests.api.crash_urls",
                DEBUG=False,
                ALLOWED_HOSTS=["*"],
            ):
                response = plain.get("/boom/", HTTP_X_REQUEST_ID="diag-500")
        assert response.status_code == 500
        assert response.headers.get("X-Request-ID") == "diag-500"
        records = [
            r
            for r in caplog.records
            if r.name == "config.middleware" and "diag-500" in r.getMessage()
        ]
        assert records, "expected a log line carrying the rid for the crash"
