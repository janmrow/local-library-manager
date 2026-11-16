"""Slice 4 release: the published OpenAPI document matches the API.

One test per write route pins both directions (request + response), so a
wrongly inferred schema fails here instead of shipping silently.
"""

import pytest


def _request_ref(doc, path, method):
    op = doc["paths"][path][method]
    return op["requestBody"]["content"]["application/json"]["schema"]["$ref"]


def _response_ref(doc, path, method, status):
    op = doc["paths"][path][method]
    return op["responses"][status]["content"]["application/json"]["schema"]["$ref"]


@pytest.mark.django_db
class TestOpenApiSchema:
    def test_schema_lists_all_v1_routes(self, client, db):
        response = client.get("/api/schema/?format=json")
        assert response.status_code == 200
        paths = response.json()["paths"]
        assert set(paths) == {
            "/api/schema/",
            "/api/v1/accounts/",
            "/api/v1/books/",
            "/api/v1/books/{id}/",
            "/api/v1/books/{id}/copies/",
            "/api/v1/loans/",
            "/api/v1/loans/{id}/",
            "/api/v1/loans/{id}/return/",
            "/api/v1/session/",
            "/api/v1/staff/loans/",
        }

    def test_schema_documents_checkout_both_directions(self, client, db):
        doc = client.get("/api/schema/?format=json").json()
        assert _request_ref(doc, "/api/v1/loans/", "post").endswith("/Checkout")
        assert _response_ref(doc, "/api/v1/loans/", "post", "201").endswith("/Loan")
        assert (
            set(doc["components"]["schemas"]["Checkout"]["properties"])
            == {"inventory_code"}
        )
        assert set(doc["components"]["schemas"]["Loan"]["properties"]) >= {
            "id",
            "inventory_code",
            "book",
            "borrowed_at",
            "returned_at",
        }

    def test_schema_documents_book_create_both_directions(self, client, db):
        doc = client.get("/api/schema/?format=json").json()
        assert _request_ref(doc, "/api/v1/books/", "post").endswith("/BookCreate")
        assert _response_ref(doc, "/api/v1/books/", "post", "201").endswith("/Book")
        assert set(doc["components"]["schemas"]["Book"]["properties"]) >= {
            "id",
            "title",
            "author",
            "available_copies",
            "total_copies",
        }

    def test_schema_documents_copy_create_both_directions(self, client, db):
        doc = client.get("/api/schema/?format=json").json()
        path = "/api/v1/books/{id}/copies/"
        assert _request_ref(doc, path, "post").endswith("/CopyCreate")
        assert _response_ref(doc, path, "post", "201").endswith("/BookCopyResponse")
        assert set(doc["components"]["schemas"]["BookCopyResponse"]["properties"]) == {
            "id",
            "inventory_code",
            "book",
        }

    def test_schema_documents_registration_both_directions(self, client, db):
        doc = client.get("/api/schema/?format=json").json()
        assert _request_ref(doc, "/api/v1/accounts/", "post").endswith("/Registration")
        assert _response_ref(doc, "/api/v1/accounts/", "post", "201").endswith(
            "/RegistrationResponse"
        )
        assert (
            set(doc["components"]["schemas"]["RegistrationResponse"]["properties"])
            == {"id", "username"}
        )

    def test_schema_documents_session_shapes(self, client, db):
        response = client.get("/api/schema/?format=json")
        assert response.status_code == 200
        body = response.json()
        schemas = body["components"]["schemas"]
        assert set(schemas["SessionState"]["properties"]) == {
            "authenticated",
            "username",
            "is_librarian",
        }
        assert set(schemas["Login"]["properties"]) == {"username", "password"}
        sign_in = body["paths"]["/api/v1/session/"]["post"]
        assert sign_in["requestBody"]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("/Login")
        assert sign_in["responses"]["200"]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("/SessionState")
        assert "204" in body["paths"]["/api/v1/session/"]["delete"]["responses"]

    def test_schema_documents_staff_lookup_param(self, client, db):
        response = client.get("/api/schema/?format=json")
        assert response.status_code == 200
        lookup = response.json()["paths"]["/api/v1/staff/loans/"]["get"]
        (param,) = [p for p in lookup["parameters"] if p["name"] == "inventory_code"]
        assert param["in"] == "query" and param["required"] is True

    def test_schema_documents_book_search_param(self, client, db):
        response = client.get("/api/schema/?format=json")
        assert response.status_code == 200
        listed = response.json()["paths"]["/api/v1/books/"]["get"]
        (param,) = [p for p in listed["parameters"] if p["name"] == "q"]
        assert param["in"] == "query" and param.get("required", False) is False

    def test_schema_documents_available_codes_as_string_array(self, client, db):
        doc = client.get("/api/schema/?format=json").json()
        codes = doc["components"]["schemas"]["Book"]["properties"]["available_codes"]
        assert codes["type"] == "array"
        assert codes["items"] == {"type": "string"}

    def test_schema_documents_book_error_envelope(self, client, db):
        doc = client.get("/api/schema/?format=json").json()
        envelope = doc["components"]["schemas"]["ErrorEnvelope"]
        assert set(envelope["properties"]) == {"code", "detail"}
        assert set(envelope["required"]) == {"code", "detail"}
        detail = doc["paths"]["/api/v1/books/{id}/"]["get"]["responses"]
        for status in ("404", "405"):
            assert detail[status]["content"]["application/json"]["schema"]["$ref"].endswith(
                "/ErrorEnvelope"
            )

    def test_schema_documents_return_without_request_body(self, client, db):
        response = client.get("/api/schema/?format=json")
        assert response.status_code == 200
        returning = response.json()["paths"]["/api/v1/loans/{id}/return/"]["post"]
        assert "requestBody" not in returning
        assert returning["responses"]["200"]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("/Loan")

    def test_schema_carries_request_id(self, client, db):
        response = client.get("/api/schema/?format=json")
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID")
