"""Process-wide chat conversation store — the longitudinal memory.

A module-level singleton so multi-turn chat sessions persist across
``/chat/stream`` calls without passing the store explicitly through every
layer. This is the fi-native memory: no hand-rolled SQLite, no keyword search —
``fi_runner.conversation`` owns persistence + history replay.

In-memory is fine for local dev (a process restart wipes sessions). Swap
``InMemoryConversationStore`` for a persistent backend when the API runs
multi-replica — same constructor arg, no other code change.
"""

from __future__ import annotations

from fi_runner.conversation import ConversationStore, InMemoryConversationStore

_CHAT_STORE: ConversationStore = InMemoryConversationStore(max_messages=40)


def chat_store() -> ConversationStore:
    """Expose the process-wide chat store (for tests / inspection)."""
    return _CHAT_STORE
