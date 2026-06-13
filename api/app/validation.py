"""Input validation helpers and tunable constants for the HTTP API."""
from __future__ import annotations

import logging
import os
import re

from fastapi import HTTPException

from .backend import normalize_backend_name

_log = logging.getLogger("app.validation")

# ---------------------------------------------------------------------------
# Tunable constants — all overridable via env vars without a code redeploy.
# ---------------------------------------------------------------------------

def _positive_int_env(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        _log.warning("%s=%r is invalid; using default %s", name, raw, default)
        return default
    if value <= 0:
        _log.warning("%s=%r must be positive; using default %s", name, raw, default)
        return default
    return value


# Hard ceiling on a single /chat/stream turn. Heavy agentic turns (multi-step
# tool use) can run several minutes — a default ~180s silently kills legitimate
# turns before the result renders. 600s is a safe net; trim the persona's depth
# so turns finish well under it, override via env for ops tuning.
CHAT_TURN_TIMEOUT_S = _positive_int_env("APP_CHAT_TURN_TIMEOUT_S", 600)

# SSE keepalive cadence. An agentic turn goes SILENT between the last tool call
# and the first text delta (the model composes — no bytes on the wire). An idle
# proxy/ingress (Azure Container Apps, nginx) resets a connection that sends
# nothing for too long; the browser then throws "network error" mid-turn. A
# comment-frame heartbeat keeps the socket warm; the client's parser ignores it.
SSE_HEARTBEAT_S = _positive_int_env("APP_SSE_HEARTBEAT_S", 15)

REQUEST_TEXT_MAX_CHARS = _positive_int_env("APP_REQUEST_TEXT_MAX_CHARS", 12_000)

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def clean_text(value: str, *, field: str, max_chars: int) -> str:
    value = value.strip()
    if not value:
        raise HTTPException(status_code=400, detail=f"{field} is empty")
    if len(value) > max_chars:
        raise HTTPException(
            status_code=413,
            detail=f"{field} is too long ({len(value)} chars); max {max_chars}",
        )
    return value


def clean_optional_id(value: str | None, *, field: str) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    validate_id(value, field=field)
    return value


def validate_id(value: str, *, field: str) -> str:
    value = value.strip()
    if not _ID_RE.fullmatch(value):
        raise HTTPException(
            status_code=400,
            detail=(
                f"{field} must be 1-128 chars and contain only letters, "
                "numbers, underscore, dot, colon, or dash"
            ),
        )
    return value


def validate_backend(backend: str | None) -> str | None:
    if backend is None:
        return None
    try:
        return normalize_backend_name(backend)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def public_error_message(exc: Exception) -> str:
    """Return a client-safe boundary error. Full details stay in server logs."""
    if isinstance(exc, TimeoutError):
        return f"turn exceeded {CHAT_TURN_TIMEOUT_S}s timeout"
    return "request failed while generating a response"
