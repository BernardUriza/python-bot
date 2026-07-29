"""Test bootstrap for the template API.

``fi_runner`` / ``fi-core`` are NOT on PyPI (conda + git only — see
environment.yml), so installing the real stack just to test our own boundary
glue would mean cloning the monorepo on every CI run. These tests target the
TEMPLATE's infrastructure layer — input validation, the API-key gate, the wire
projections, the SSE heartbeat pump, the /health probe — none of which depend on
fi_runner's behaviour. So we register a minimal stub of fi_runner here; the real
package shadows it transparently when present (we only install the stub if the
real import fails). This keeps the test job to a plain `pip install fastapi …`.
"""

from __future__ import annotations

import sys
import types


def _install_fi_runner_stub() -> None:
    try:
        import fi_runner  # noqa: F401 — real package present, use it
        return
    except ModuleNotFoundError:
        pass

    fi_runner = types.ModuleType("fi_runner")

    class _Stub:
        """Records constructor kwargs so tests can assert on composition."""

        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class _PermissionMode:
        BYPASS = "bypass"

    def _antidrift_guard(**kwargs):
        return ("antidrift_guard", kwargs)

    packs = types.ModuleType("fi_runner.packs")
    packs.DEFAULT_EN = ["as an AI", "as a language model"]
    packs.DEFAULT_ES = ["como una IA"]
    packs.MARKDOWN_DRIFT = []
    packs.STAGE_DIRECTIONS = []
    packs.GENERIC_REINFORCEMENT = "Stay in character."

    class _ConversationStore:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

    conversation = types.ModuleType("fi_runner.conversation")
    conversation.ConversationStore = _ConversationStore
    conversation.InMemoryConversationStore = _ConversationStore

    fi_runner.MCPServerSpec = _Stub
    fi_runner.PermissionMode = _PermissionMode
    fi_runner.RetryPolicy = _Stub
    fi_runner.Runner = _Stub
    fi_runner.ToolPolicy = _Stub
    fi_runner.ClaudeCodeBackend = _Stub
    fi_runner.CodexBackend = _Stub
    fi_runner.antidrift_guard = _antidrift_guard
    fi_runner.packs = packs
    fi_runner.conversation = conversation

    sys.modules["fi_runner"] = fi_runner
    sys.modules["fi_runner.packs"] = packs
    sys.modules["fi_runner.conversation"] = conversation


_install_fi_runner_stub()
