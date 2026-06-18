"""Process-wide content store for the CMS module.

In-memory by default (a restart wipes it) — fine for the tracer bullet and local
dev. Swap ``InMemoryContentStore`` for a Postgres-backed one (same methods) when
an org's content must survive multi-replica, mirroring how ``app.store`` swaps
the conversation backend. No other code changes.
"""
from __future__ import annotations

import time
import uuid

from .models import ContentDraft, ContentItem, ContentPatch


class SlugTaken(Exception):
    """Raised when a create/patch would collide with an existing slug."""


class InMemoryContentStore:
    def __init__(self) -> None:
        self._items: dict[str, ContentItem] = {}

    def clear(self) -> None:
        self._items.clear()

    def _slug_owner(self, slug: str) -> str | None:
        for item in self._items.values():
            if item.slug == slug:
                return item.id
        return None

    def create(self, draft: ContentDraft) -> ContentItem:
        if self._slug_owner(draft.slug) is not None:
            raise SlugTaken(draft.slug)
        now = time.time()
        item = ContentItem(
            id=uuid.uuid4().hex,
            slug=draft.slug,
            type=draft.type,
            title=draft.title,
            body=draft.body,
            author=draft.author,
            status="draft",
            created_at=now,
            updated_at=now,
        )
        self._items[item.id] = item
        return item

    def get(self, item_id: str) -> ContentItem | None:
        return self._items.get(item_id)

    def get_published_by_slug(self, slug: str) -> ContentItem | None:
        for item in self._items.values():
            if item.slug == slug and item.status == "published":
                return item
        return None

    def list(self, *, published_only: bool) -> list[ContentItem]:
        items = self._items.values()
        if published_only:
            items = [i for i in items if i.status == "published"]
        return sorted(items, key=lambda i: i.created_at)

    def patch(self, item_id: str, patch: ContentPatch) -> ContentItem | None:
        item = self._items.get(item_id)
        if item is None:
            return None
        fields = patch.model_dump(exclude_unset=True)
        new_slug = fields.get("slug")
        if new_slug is not None:
            owner = self._slug_owner(new_slug)
            if owner is not None and owner != item_id:
                raise SlugTaken(new_slug)
        updated = item.model_copy(update={
            **fields,
            "updated_at": max(time.time(), item.updated_at),
        })
        self._items[item_id] = updated
        return updated

    def publish(self, item_id: str) -> ContentItem | None:
        item = self._items.get(item_id)
        if item is None:
            return None
        updated = item.model_copy(update={
            "status": "published",
            "updated_at": max(time.time(), item.updated_at),
        })
        self._items[item_id] = updated
        return updated

    def delete(self, item_id: str) -> bool:
        return self._items.pop(item_id, None) is not None


_CONTENT_STORE = InMemoryContentStore()


def content_store() -> InMemoryContentStore:
    """Expose the process-wide content store (for routes / tests / inspection)."""
    return _CONTENT_STORE
