"""Builds the template agent on top of fi_runner.

THIS IS THE SEAM. A fresh project fills three things here and ships:
  1. the persona (``personas/<name>.md`` — content, not code),
  2. the MCP servers the agent may call (``_MCP_SERVERS`` below — empty by
     default),
  3. the capabilities + guards your product needs.

Everything else (backend factory + cache, conversation store, wire schemas,
SSE plumbing) is template infrastructure you should not need to touch.

Extracted siblings:
  backend.py   — backend factory + process-wide singleton cache (claude/codex)
  store.py     — process-wide ConversationStore singleton (longitudinal memory)
  guards.py    — generic anti-drift guard chain
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from fi_runner import (
    MCPServerSpec,  # noqa: F401 — re-exported for the MCP seam below
    PermissionMode,
    RetryPolicy,
    Runner,
    ToolPolicy,
)
from fi_runner.conversation import ConversationStore

from .backend import _get_backend, normalize_backend_name
from .guards import build_guards
from .store import _CHAT_STORE, chat_store

_log = logging.getLogger(__name__)

# --- Persona ------------------------------------------------------------------
# Prompts live in files (personas/<name>.md), NOT hardcoded — the voice is
# content that iterates fast. Editing it never touches this module.
_PERSONAS_DIR = Path(__file__).parent / "personas"


def load_persona(name: str) -> str:
    """Load a persona prompt from ``personas/<name>.md`` (content, not code)."""
    return (_PERSONAS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()


ASSISTANT_PERSONA = load_persona("assistant")

# --- MCP seam -----------------------------------------------------------------
# Declare the MCP servers the agent may call. The template ships with NONE so
# it boots and answers with the model + native tools only. Add yours here:
#
#   _MCP_SERVERS = [
#       MCPServerSpec(name="fetch", command="npx", args=["-y", "some-mcp"]),
#   ]
#
# Whatever credential the server reads should come from an env var passthrough
# (set on the Container App, never baked into the image).
_MCP_SERVERS: list[MCPServerSpec] = []

__all__ = [
    "build_runner",
    "chat_store",
    "chat_stream",
    "load_persona",
    "normalize_backend_name",
]


def build_runner(
    backend: str | None = None,
    *,
    with_rag: bool = False,
    conversation_store: ConversationStore | None = None,
    on_event: Callable[[str, dict], None] | None = None,
) -> Runner:
    """Compose a fi_runner Runner with the chosen backend + the MCP seam.

    The Runner itself is cheap (a config holder); the BACKEND is the expensive
    bit and it's cached process-wide — see :func:`backend._get_backend`.
    """
    backend_name = normalize_backend_name(backend)
    agent_backend = _get_backend(backend_name)

    capability_names: list[str] = ["task_tracker"]
    if with_rag:
        capability_names.append("rag_store")

    return Runner(
        backend=agent_backend,
        persona=ASSISTANT_PERSONA,
        extra_mcp_servers=_MCP_SERVERS,
        capabilities=capability_names,
        # BYPASS = auto-approve tool calls. Requires a non-root user in the
        # container (Claude Code refuses BYPASS as root — the Dockerfile sets
        # up the `runner` user). Native WebSearch/WebFetch stay enabled so the
        # template agent can reach the web out of the box; lock them down here
        # if you route all web access through an MCP instead.
        tool_policy=ToolPolicy(permission_mode=PermissionMode.BYPASS),
        guards=build_guards(),
        retry_policy=RetryPolicy(max_attempts=2),
        conversation_store=conversation_store,
        on_event=on_event,
    )


async def chat_stream(
    message: str,
    *,
    session_id: str,
    backend: str | None = None,
    corpus_id: str | None = None,
    on_event: Callable[[str, dict], None] | None = None,
):
    """Stream a chat turn as dict events (chain-of-thought).

    Yields, in order:
      - ``{"type":"tool_call","tool":ToolCall}`` per tool/MCP call,
      - ``{"type":"text","text":delta}`` as the assistant text arrives,
      - ``{"type":"result","result":TurnResult}`` once guards settle.

    The ConversationStore replays prior turns for ``session_id`` automatically —
    that's the longitudinal memory; the caller just passes the raw message.
    """
    runner = build_runner(
        backend,
        with_rag=bool(corpus_id),
        conversation_store=_CHAT_STORE,
        on_event=on_event,
    )
    async for event in runner.run_stream(message, session_id=session_id):
        yield event
