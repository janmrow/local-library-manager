"""JSON error envelope for API errors (slice 2: 400/403/404 in envelope)."""

from rest_framework.views import exception_handler


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
    if response is None or not isinstance(response.data, dict):
        return response
    if "code" in response.data:
        return response
    if response.status_code == 400:
        response.data = {"code": "invalid", "detail": _flatten_detail(response.data)}
    elif response.status_code == 403:
        response.data = {"code": "forbidden", "detail": _flatten_detail(response.data)}
    elif response.status_code == 404:
        response.data = {
            "code": "not_found",
            "detail": response.data.get("detail", "Not found."),
        }
    return response
