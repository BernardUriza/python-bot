"""Content shapes for the CMS module. ``extra = "forbid"`` everywhere — an org's
self-publish form should fail loudly on an unknown field, not swallow it."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ContentType = Literal["post", "doc", "page"]
ContentStatus = Literal["draft", "published"]

SLUG_MAX = 160
TITLE_MAX = 300
BODY_MAX = 200_000  # a long crónica, not a book


class ContentDraft(BaseModel):
    """Create payload. ``status`` is server-controlled (always starts draft)."""

    slug: str = Field(..., min_length=1, max_length=SLUG_MAX)
    type: ContentType = "post"
    title: str = Field(..., min_length=1, max_length=TITLE_MAX)
    body: str = Field(..., min_length=1, max_length=BODY_MAX)
    author: str = Field(..., min_length=1, max_length=TITLE_MAX)

    class Config:
        extra = "forbid"


class ContentPatch(BaseModel):
    """Update payload — every field optional; only those present are applied."""

    slug: str | None = Field(default=None, min_length=1, max_length=SLUG_MAX)
    type: ContentType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX)
    body: str | None = Field(default=None, min_length=1, max_length=BODY_MAX)
    author: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX)

    class Config:
        extra = "forbid"


class ContentItem(BaseModel):
    """Stored + returned shape."""

    id: str
    slug: str
    type: ContentType
    title: str
    body: str
    author: str
    status: ContentStatus
    created_at: float
    updated_at: float
