"""Slice 4 release: the published OpenAPI document matches the API."""

import pytest


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

    def test_schema_documents_checkout_shape_not_loan(self, client, db):
        response = client.get("/api/schema/?format=json")
        assert response.status_code == 200
        body = response.json()
        create = body["paths"]["/api/v1/loans/"]["post"]
        ref = create["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        assert ref.endswith("/Checkout")
        assert set(body["components"]["schemas"]["Checkout"]["properties"]) == {
            "inventory_code"
        }

    def test_schema_documents_book_create_response(self, client, db):
        response = client.get("/api/schema/?format=json")
        assert response.status_code == 200
        body = response.json()
        create = body["paths"]["/api/v1/books/"]["post"]
        ref = create["responses"]["201"]["content"]["application/json"]["schema"]["$ref"]
        assert ref.endswith("/Book")
        assert (
            set(body["components"]["schemas"]["Book"]["properties"])
            >= {"id", "title", "author", "available_copies", "total_copies"}
        )

    def test_schema_documents_copy_create_response(self, client, db):
        response = client.get("/api/schema/?format=json")
        assert response.status_code == 200
        body = response.json()
        add_copy = body["paths"]["/api/v1/books/{id}/copies/"]["post"]
        ref = add_copy["responses"]["201"]["content"]["application/json"]["schema"]["$ref"]
        assert ref.endswith("/BookCopyResponse")
        assert (
            set(body["components"]["schemas"]["BookCopyResponse"]["properties"])
            == {"id", "inventory_code", "book"}
        )

    def test_schema_documents_registration_without_password(self, client, db):
        response = client.get("/api/schema/?format=json")
        assert response.status_code == 200
        body = response.json()
        register = body["paths"]["/api/v1/accounts/"]["post"]
        ref = register["responses"]["201"]["content"]["application/json"]["schema"]["$ref"]
        assert ref.endswith("/RegistrationResponse")
        assert (
            set(body["components"]["schemas"]["RegistrationResponse"]["properties"])
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

    def test_schema_documents_return_without_request_body(self, client, db):
        response = client.get("/api/schema/?format=json")
        assert response.status_code == 200
        returning = response.json()["paths"]["/api/v1/loans/{id}/return/"]["post"]
        assert "requestBody" not in returning
        assert "200" in returning["responses"]

    def test_schema_carries_request_id(self, client, db):
        response = client.get("/api/schema/?format=json")
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID")
