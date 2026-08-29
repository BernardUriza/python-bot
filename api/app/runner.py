"""Builds the template agent on top of fi_runner.

THIS IS THE SEAM. A fresh project fills three things here and ships:
  1. the persona (``personas/<name>.md`` — content, not code),
  2. the guards your product needs (``guards.py``),
  3. the AIRE registry tools the agent may call — in ``backend.BASE_TOOLS``, NOT
     here: on the AIRE route tools are mounted server-side, so a local MCP spec
     in ``_MCP_SERVERS`` below never runs (read the note on it).

Everything else (backend factory + cache, conversation store, wire schemas,
SSE plumbing) is template infrastructure you should not need to touch.

Extracted siblings:
  backend.py   — AIRE door client factory + process-wide cache
  store.py     — process-wide ConversationStore singleton (longitudinal memory)
  guards.py    — generic anti-drift guard chain
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from fi_runner import (
    MCPServerSpec,  # noqa: F401 — re-exported for the MCP seam below
    RetryPolicy,
    Runner,
    ToolPolicy,
)
from fi_runner.conversation import ConversationStore

from .backend import get_backend
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
# Declare the MCP servers the agent may call. The template ships with NONE.
#
#   _MCP_SERVERS = [
#       MCPServerSpec(name="fetch", command="npx", args=["-y", "some-mcp"]),
#   ]
#
# READ THIS BEFORE FILLING IT IN. On the AIRE route a local MCP server does NOT
# reach the agent: only the spec's NAME crosses the door, and AIRE mounts its
# OWN vetted server of that name — a name outside its registry is rejected with
# a 422. So a `command`/`args` you write here never runs anywhere. Tools that
# actually reach the model are named in `backend.BASE_TOOLS` and must exist in
# AIRE's registry first. Keep this list empty unless you are deliberately
# addressing a registry tool by spec.
_MCP_SERVERS: list[MCPServerSpec] = []

__all__ = [
    "build_runner",
    "chat_store",
    "chat_stream",
    "load_persona",
]


def build_runner(
    *,
    with_rag: bool = False,
    conversation_store: ConversationStore | None = None,
    on_event: Callable[[str, dict], None] | None = None,
) -> Runner:
    """Compose a fi_runner Runner over the AIRE door.

    The Runner itself is cheap (a config holder); the BACKEND holds the pooled
    HTTP client and is cached process-wide — see :func:`backend.get_backend`.
    """
    return Runner(
        backend=get_backend(with_rag=with_rag),
        persona=ASSISTANT_PERSONA,
        extra_mcp_servers=_MCP_SERVERS,
        # No local capabilities: AIRE mounts its tools server-side, so the
        # names go on the backend (`registry_tools`) and this list stays empty.
        # Spawning fi-core MCP subprocesses here would cost the subprocess and
        # reach nobody.
        capabilities=[],
        # AIRE does NOT forward tool_policy — it configures tools server-side,
        # and the builtin surface is chosen by the door mode (`APP_AIRE_MODE`,
        # default "agent" = the native web tools this template shipped with).
        # A non-default policy here would only earn a warning per turn.
        tool_policy=ToolPolicy(),
        guards=build_guards(),
        retry_policy=RetryPolicy(max_attempts=2),
        conversation_store=conversation_store,
        on_event=on_event,
    )


async def chat_stream(
    message: str,
    *,
    session_id: str,
    corpus_id: str | None = None,
    on_event: Callable[[str, dict], None] | None = None,
):
    """Stream a chat turn as dict events (chain-of-thought).

    Yields, in order:
      - ``{"type":"tool_call","tool":ToolCall}`` per tool/MCP call,
      - ``{"type":"text","text":delta}`` as the assistant text arrives,
      - ``{"type":"result","result":TurnResult}`` once guards settle.

    Memory: AIRE owns the transcript for a session it already holds, so the
    Runner RESUMES it instead of re-sending the history as prompt text. The
    ConversationStore below stays as the fallback that replays prior turns for a
    session AIRE has never seen (a fresh casita, an unreachable door).
    """
    runner = build_runner(
        with_rag=bool(corpus_id),
        conversation_store=_CHAT_STORE,
        on_event=on_event,
    )
    async for event in runner.run_stream(message, session_id=session_id):
        yield event
