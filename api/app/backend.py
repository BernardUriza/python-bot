"""Backend factory and process-wide singleton cache.

Owns the two backend types (claude / codex), their construction logic, and the
cache that keeps the SDK clients + MCP subprocess pool alive across turns.
Runner imports ``_get_backend`` and ``normalize_backend_name``; nothing else
needs to reach in here.

Auth note (claude only): the Claude Agent SDK gives an ambient
``ANTHROPIC_API_KEY`` priority over the OAuth token, silently hijacking
subscription auth. When an OAuth token is present we drop any ambient key so
the Max subscription wins. No-op in the container (the entrypoint env carries
no ANTHROPIC_API_KEY).

Cache rationale: constructing a ``ClaudeCodeBackend`` / ``CodexBackend`` spawns
SDK clients and an MCP subprocess pool — ~1-3s overhead. ``_get_backend``
returns a process-wide singleton keyed by backend name so the second chat turn
reuses the same backend instance without re-spawning subprocesses.
"""

from __future__ import annotations

import os
from typing import Literal

from fi_runner import ClaudeCodeBackend, CodexBackend

BackendName = Literal["claude", "codex"]
_VALID_BACKENDS: set[str] = {"claude", "codex"}

_BACKENDS: dict[str, ClaudeCodeBackend | CodexBackend] = {}


def normalize_backend_name(backend: str | None = None) -> BackendName:
    """Resolve and validate the requested backend name.

    Unknown values fail fast with a clear ValueError (the API maps it to HTTP
    400) instead of silently falling back to a default provider — an
    operational typo that routes traffic to the wrong backend is hard to
    diagnose otherwise.
    """
    name = (backend or os.getenv("APP_BACKEND", "claude")).strip().lower()
    if name not in _VALID_BACKENDS:
        raise ValueError(
            f"unsupported backend {name!r}; expected one of {sorted(_VALID_BACKENDS)}"
        )
    return name  # type: ignore[return-value]


def _make_backend(name: str) -> ClaudeCodeBackend | CodexBackend:
    """Construct the agent backend for ``name`` (``claude`` | ``codex``)."""
    name = normalize_backend_name(name)
    if name == "codex":
        return CodexBackend(
            default_model=os.getenv("APP_MODEL_CODEX", "gpt-4.1"),
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        )
    if os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        os.environ.pop("ANTHROPIC_API_KEY", None)
    return ClaudeCodeBackend(
        default_model=os.getenv("APP_MODEL", "claude-sonnet-4-5"),
    )


def _get_backend(name: str) -> ClaudeCodeBackend | CodexBackend:
    """Process-wide backend cache (one per name)."""
    name = normalize_backend_name(name)
    inst = _BACKENDS.get(name)
    if inst is None:
        inst = _make_backend(name)
        _BACKENDS[name] = inst
    return inst
