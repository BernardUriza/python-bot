"""HTTP face for the CMS module.

Public reads (the published feed + a single published item by slug) are UNGATED
so an org's website can render them with no key. Everything that writes — create,
patch, publish, delete — and the admin listing that exposes drafts go through
``verify_api_key`` (fail-open in dev, enforced once APP_API_KEY is set).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import verify_api_key
from .models import ContentDraft, ContentItem, ContentPatch
from .store import SlugTaken, content_store

cms_router = APIRouter(prefix="/cms", tags=["cms"])

_gated = [Depends(verify_api_key)]


@cms_router.post("/content", status_code=201, dependencies=_gated)
async def create_content(draft: ContentDraft) -> ContentItem:
    try:
        return content_store().create(draft)
    except SlugTaken:
        raise HTTPException(status_code=409, detail=f"slug already exists: {draft.slug}")


@cms_router.put("/content/{item_id}", dependencies=_gated)
async def update_content(item_id: str, patch: ContentPatch) -> ContentItem:
    try:
        item = content_store().patch(item_id, patch)
    except SlugTaken as e:
        raise HTTPException(status_code=409, detail=f"slug already exists: {e}")
    if item is None:
        raise HTTPException(status_code=404, detail="content not found")
    return item


@cms_router.post("/content/{item_id}/publish", dependencies=_gated)
async def publish_content(item_id: str) -> ContentItem:
    item = content_store().publish(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="content not found")
    return item


@cms_router.delete("/content/{item_id}", status_code=204, dependencies=_gated)
async def delete_content(item_id: str) -> None:
    if not content_store().delete(item_id):
        raise HTTPException(status_code=404, detail="content not found")


@cms_router.get("/content")
async def list_published() -> list[ContentItem]:
    return content_store().list(published_only=True)


@cms_router.get("/admin/content", dependencies=_gated)
async def list_all() -> list[ContentItem]:
    return content_store().list(published_only=False)


@cms_router.get("/content/{slug}")
async def get_published(slug: str) -> ContentItem:
    item = content_store().get_published_by_slug(slug)
    if item is None:
        raise HTTPException(status_code=404, detail="published content not found")
    return item
