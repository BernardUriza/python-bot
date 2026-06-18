"""FastAPI face for the fi-based template. Exposes POST /chat/stream — a
multi-turn chat with live chain-of-thought (SSE) — plus an ungated /health
that the Container App liveness probe and the deploy smoke test hit."""

from __future__ import annotations

import logging
import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .auth import limiter
from .modules import enabled_optional_modules
from .observability import request_observability_middleware
from .routes import chat_router

# Ensure our logger surfaces in uvicorn's stdout/stderr. uvicorn configures the
# `uvicorn.*` loggers but leaves the root handler-less in some setups — without
# this, `app.*.info(...)` calls silently disappear. Idempotent on --reload.
_root_log = logging.getLogger()
if not _root_log.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
logging.getLogger("app").setLevel(logging.INFO)
_log = logging.getLogger("app.app")
APP_VERSION = "0.1.0"
APP_NAME = os.getenv("APP_NAME", "fi-template-api")
_STARTED_AT = time.time()

_log.info("logging cabled — chat router registered")

app = FastAPI(title=APP_NAME, version=APP_VERSION)
app.middleware("http")(request_observability_middleware)

# CORS — accept origins listed in CORS_ALLOW_ORIGINS (comma-separated) or
# fall back to wide-open in dev. Production sets this to the SWA URL via
# Container App env var.
_cors_origins_env = (os.getenv("CORS_ALLOW_ORIGINS") or "").strip()
_cors_origins = (
    [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
    if _cors_origins_env
    else ["*"]
)
if _cors_origins == ["*"]:
    _log.warning(
        "CORS_ALLOW_ORIGINS unset — accepting requests from any origin "
        "(dev convenience). Set the env var in production to lock CORS to "
        "the SWA URL."
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Server-Timing"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(chat_router)

# Optional, opt-in capabilities. The chat router above is always on; these mount
# only when named in APP_MODULES (see app.modules). Lazy-imported inside the
# guard so a plain assistant never pays the import cost of a module it disabled.
_optional = enabled_optional_modules()
if "cms" in _optional:
    from .cms import cms_router

    app.include_router(cms_router)
    _log.info("optional module mounted: cms")


@app.get("/health")
async def health() -> dict:
    # Intentionally UNGATED — Container Apps' liveness probe and the deploy
    # smoke test must reach this without a key. Returns ok even when
    # APP_API_KEY is unset.
    return {
        "ok": True,
        "service": APP_NAME,
        "version": APP_VERSION,
        "uptime_s": round(time.time() - _STARTED_AT, 2),
    }
