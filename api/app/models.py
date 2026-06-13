"""Pydantic request models for the template HTTP API."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .validation import REQUEST_TEXT_MAX_CHARS


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=REQUEST_TEXT_MAX_CHARS)
    backend: str | None = None  # "claude" | "codex" (only claude streams live)
    # Optional RAG corpus. When set, the rag_store capability is wired for the
    # turn so the agent can search_documents over it. Leave unset to skip RAG.
    corpus_id: str | None = Field(default=None, max_length=128)

    class Config:
        extra = "forbid"
