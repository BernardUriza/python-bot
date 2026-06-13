"""Small observability primitives shared by the FastAPI app.

The service mostly fails at external boundaries: browser -> API, API -> agent,
API -> MCP/RAG providers. A stable request id plus one access log per HTTP
request is enough to correlate those failures without pulling in a full tracing
stack.
"""

from __future__ import annotations

import contextvars
import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

_log = logging.getLogger("app.http")

_REQUEST_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "app_request_id",
    default="-",
)


def current_request_id() -> str:
    """Return the active HTTP request id, or ``"-"`` outside a request."""
    return _REQUEST_ID.get()


def _clean_request_id(value: str | None) -> str:
    value = " ".join((value or "").strip().split())
    if not value:
        return uuid.uuid4().hex
    # Keep log lines and response headers bounded even if a client sends junk.
    return value[:96]


async def request_observability_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach request id/timing headers and emit one structured-ish access log."""
    request_id = _clean_request_id(
        request.headers.get("x-request-id")
        or request.headers.get("x-client-request-id")
    )
    token = _REQUEST_ID.set(request_id)
    started = time.perf_counter()
    status_code = 500
    response: Response | None = None
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        _log.exception(
            "http.request_failed request_id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
        )
        raise
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        if response is not None:
            response.headers["X-Request-ID"] = request_id
            response.headers["Server-Timing"] = f"app;dur={duration_ms}"

        client = request.client.host if request.client else "-"
        _log.info(
            "http.request request_id=%s method=%s path=%s status=%s duration_ms=%.2f client=%s",
            request_id,
            request.method,
            request.url.path,
            status_code,
            duration_ms,
            client,
        )
        _REQUEST_ID.reset(token)
