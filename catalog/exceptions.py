"""JSON error envelope for API errors (4xx always carry {"code", "detail"})."""

from rest_framework.views import exception_handler

# Explicit codes for client errors handled by the fallback branch below.
# Anything else 4xx falls back to "invalid".
_CLIENT_ERROR_CODES = {
    401: "unauthenticated",
    404: "not_found",
    415: "unsupported_media_type",
    429: "too_many_requests",
}


def _flatten_detail(data) -> str:
    if isinstance(data, dict):
        parts = []
        for field, errors in data.items():
            if isinstance(errors, (list, tuple)):
                for error in errors:
                    parts.append(f"{field}: {error}" if field != "detail" else str(error))
            else:
                parts.append(f"{field}: {errors}" if field != "detail" else str(errors))
        return "; ".join(parts) if parts else "Invalid request."
    if isinstance(data, list):
        return "; ".join(str(item) for item in data)
    return str(data)


def catalogue_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response
    if isinstance(response.data, dict) and "code" in response.data:
        return response
    if response.status_code == 400:
        response.data = {"code": "invalid", "detail": _flatten_detail(response.data)}
    elif response.status_code == 403:
        response.data = {"code": "forbidden", "detail": _flatten_detail(response.data)}
    elif response.status_code == 405:
        response.data = {
            "code": "method_not_allowed",
            "detail": _flatten_detail(response.data),
        }
    elif response.status_code == 404 and isinstance(response.data, dict):
        response.data = {
            "code": "not_found",
            "detail": response.data.get("detail", "Not found."),
        }
    elif 400 <= response.status_code < 500:
        code = _CLIENT_ERROR_CODES.get(response.status_code, "invalid")
        response.data = {"code": code, "detail": _flatten_detail(response.data)}
    return response
