"""Pydantic request models for the template HTTP API."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .validation import REQUEST_TEXT_MAX_CHARS


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=REQUEST_TEXT_MAX_CHARS)
    # NOTE: there is no `backend` field. It selected claude/codex and died with
    # them (2026-08-29) — dropped rather than kept as an ignored no-op, so a
    # client can never believe it picked a transport. `extra="forbid"` below
    # means an old client still sending it gets a 422, which is the point.
    #
    # Optional RAG corpus. When set, AIRE's `rag_store` tool is requested for the
    # turn so the agent can search documents. Leave unset to skip RAG.
    corpus_id: str | None = Field(default=None, max_length=128)

    model_config = ConfigDict(extra="forbid")
