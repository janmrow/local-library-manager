"""Slice 4 observability: X-Request-ID is generated, propagated, and logged."""

import logging
import re
import uuid

import pytest

from catalog.models import Book, BookCopy
from config.middleware import RequestIdMiddleware


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
