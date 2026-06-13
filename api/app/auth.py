"""API-key gate and per-IP rate limiter for the template HTTP API.

Threat model: a casual crawler that finds the public Container App URL and
starts hitting /chat/stream — each turn burns agent tokens (and any MCP/credit
the seam wires in). A constant-time match against APP_API_KEY is the floor that
stops that. Fail-open in dev (env var unset) so smoke tests work without
ceremony.
"""
from __future__ import annotations

import hmac
import logging
import os

from fastapi import Header, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

_log = logging.getLogger("app.auth")

_API_KEY = (os.getenv("APP_API_KEY") or "").strip() or None
if _API_KEY is None:
    _log.warning(
        "APP_API_KEY is unset — /chat/stream is UNAUTHENTICATED (fail-open). "
        "Set the env var in production."
    )

# Per-IP rate limit. Even a leaked key shouldn't let one client drain the
# agent budget. get_remote_address trusts X-Forwarded-For only behind a
# properly-configured reverse proxy — Azure Container Apps sets it.
limiter = Limiter(key_func=get_remote_address)


async def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Dependency: 401 if a key is configured AND the request doesn't match.
    No-op when no key is configured (dev convenience).

    Constant-time compare via hmac.compare_digest to prevent timing attacks."""
    if _API_KEY is None:
        return  # fail-open in dev
    supplied = (x_api_key or "").strip()
    if not supplied or not hmac.compare_digest(supplied, _API_KEY):
        raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")
