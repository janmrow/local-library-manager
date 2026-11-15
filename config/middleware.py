"""Global observability middleware (slice 4: X-Request-ID)."""

import logging
import re
import time
import uuid

logger = logging.getLogger(__name__)

# Client-supplied IDs are echoed into the response header and the log line,
# so only a tight allowlist is accepted. Anything else falls back to a
# generated UUID: the ID never rejects a request and is never truncated
# and echoed back.
REQUEST_ID_RE = re.compile(r"[A-Za-z0-9-]{1,64}")


class RequestIdMiddleware:
    """Generate or propagate X-Request-ID and log the request.

    Reads the incoming ``X-Request-ID`` header; when absent, blank, or
    outside the allowlist, generates a random UUID4 value. The same value
    is returned on the response and included with method, path, status,
    and duration in the server log, so an HTTP response can be matched
    to its log line and then to the loan rows in PostgreSQL.
    """

    HEADER = "X-Request-ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def _resolve_id(self, request) -> str:
        incoming = (request.headers.get(self.HEADER) or "").strip()
        if REQUEST_ID_RE.fullmatch(incoming):
            return incoming
        return str(uuid.uuid4())

    def _log(self, request, status: int, duration_ms: float, request_id: str) -> None:
        logger.info(
            "%s %s %s %.1fms rid=%s",
            request.method,
            request.path,
            status,
            duration_ms,
            request_id,
        )

    def __call__(self, request):
        request_id = self._resolve_id(request)
        request.request_id = request_id
        start = time.monotonic()
        try:
            response = self.get_response(request)
        except Exception:
            # A crash still gets a log line with the ID (the case README
            # diagnosis needs most); there is no response to attach it to.
            self._log(request, 500, (time.monotonic() - start) * 1000, request_id)
            raise
        duration_ms = (time.monotonic() - start) * 1000
        response[self.HEADER] = request_id
        self._log(request, response.status_code, duration_ms, request_id)
        return response
