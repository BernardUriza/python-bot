"""AIRE backend factory and process-wide singleton cache.

ONE route, one door. The template used to carry two backends (``claude`` /
``codex``) selected by ``APP_BACKEND``; fi-runner deleted ``ClaudeCodeBackend``,
``CodexBackend`` and ``SubprocessCLIBackend`` on 2026-08-29, so ``AIREBackend``
is the only backend there is and the switch it was chosen with is gone with it.
Runner imports :func:`get_backend`; nothing else needs to reach in here.

What AIRE is, and why this file got shorter: AIRE is Bernard's always-up server
that wraps the Claude Agent SDK. It owns the session transcript (its Postgres),
the tool registry and the permissions — all SERVER-side. So this backend is thin
by design: no SDK client to construct, no MCP subprocess pool to keep warm, no
CLI to install in the image, no OAuth credential to materialize at boot. What
crosses the wire is HTTPS to AIRE's door.

Config — both required, read from the env by ``AIREBackend`` itself:
  ``AIRE_GATE_URL``    the door's base URL
  ``AIRE_AUTH_TOKEN``  the long bearer secret (an ``AIRE_CANARY_TOKEN`` works too)
Tunable here:
  ``APP_AIRE_PROJECT`` the casita this app addresses (default ``python-bot``)
  ``APP_MODEL``        forwarded per turn; AIRE pins it on the session's client
  ``APP_AIRE_MODE``    ``agent`` (default) or ``complete`` — see :data:`AIRE_MODE`

Cache rationale: an ``AIREBackend`` holds a pooled ``httpx.AsyncClient`` plus the
per-casita ``/init`` state, so it is built once per tool shape and reused across
turns. It is also why :func:`close_backends` exists — a door client nobody closes
leaks its connections and TLS sessions past shutdown.
"""

from __future__ import annotations

import logging
import os

from fi_runner import AIREBackend

_log = logging.getLogger("app.backend")

# The AIRE casita this app talks to. Rename it per project — it is the app's
# identity server-side, and it must match AIRE's allowlist ([A-Za-z0-9_-], 128).
DEFAULT_PROJECT = "python-bot"

# The door mode EVERY turn rides. AIRE governs tools server-side, so this — not
# a ToolPolicy — is how a consumer picks its builtin surface:
#   "complete" → no builtins at all (a pure conversational/classifying turn)
#   "agent"    → Read / Write / Glob / Grep / WebSearch / WebFetch, caged to the
#                casita. Bash is prohibited in BOTH.
# The template defaults to "agent" because it shipped with native web access out
# of the box; drop it to "complete" for an app that must not reach the network.
AIRE_MODE = (os.getenv("APP_AIRE_MODE") or "agent").strip().lower()

# Vetted tool NAMES from AIRE's own registry, requested on every turn. These are
# NAMES, not specs: local MCP capabilities cannot cross the door (AIRE mounts its
# own in-process server of that name and 422s any name its registry does not
# ship). Adding a local MCP server to runner.py's seam therefore does NOT reach
# the agent on this route — the tool has to exist in AIRE's registry first.
BASE_TOOLS: tuple[str, ...] = ("task_tracker",)
RAG_TOOL = "rag_store"

_BACKENDS: dict[tuple[str, ...], AIREBackend] = {}


def aire_project() -> str:
    """The casita this app addresses."""
    return (os.getenv("APP_AIRE_PROJECT") or DEFAULT_PROJECT).strip() or DEFAULT_PROJECT


def turn_tools(*, with_rag: bool = False) -> tuple[str, ...]:
    """The AIRE registry tools a turn asks for. RAG stays opt-in per turn (the
    caller passes a ``corpus_id``), same seam as before the migration."""
    return (*BASE_TOOLS, RAG_TOOL) if with_rag else BASE_TOOLS


def _make_backend(tools: tuple[str, ...]) -> AIREBackend:
    """Construct the door client for one tool shape."""
    return AIREBackend(
        project=aire_project(),
        default_model=os.getenv("APP_MODEL", "claude-sonnet-4-5"),
        default_mode=AIRE_MODE,
        registry_tools=tools,
    )


def get_backend(*, with_rag: bool = False) -> AIREBackend:
    """Process-wide door client, one per tool shape (created on first use)."""
    tools = turn_tools(with_rag=with_rag)
    backend = _BACKENDS.get(tools)
    if backend is None:
        backend = _make_backend(tools)
        _BACKENDS[tools] = backend
    return backend


async def close_backends() -> None:
    """Drain every door client this process opened (call on shutdown).

    Best-effort per backend: one refusing to close must not strand the rest.
    """
    backends = list(_BACKENDS.values())
    _BACKENDS.clear()
    for backend in backends:
        try:
            await backend.aclose()
        except Exception:  # noqa: BLE001 - shutdown must not raise
            _log.warning("AIRE backend refused to close cleanly", exc_info=True)
