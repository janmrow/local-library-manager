"""JSON error envelope for catalogue errors (slice 1: 404 only)."""

from rest_framework.views import exception_handler


def catalogue_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if (
        response is not None
        and response.status_code == 404
        and isinstance(response.data, dict)
        and "code" not in response.data
    ):
        response.data = {
            "code": "not_found",
            "detail": response.data.get("detail", "Not found."),
        }
    return response
