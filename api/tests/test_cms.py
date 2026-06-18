"""TDD for the opt-in CMS module — a content manager an org self-publishes to.

These tests are fi-INDEPENDENT: they mount `cms_router` on a bare FastAPI app,
never importing `app.app` (which pulls in fi_runner). Run in any env with
fastapi+httpx+pytest:  python -m pytest tests/test_cms.py
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.cms import cms_router
from app.cms.store import content_store


@pytest.fixture()
def client() -> TestClient:
    content_store().clear()  # isolate each test from the process-wide singleton
    app = FastAPI()
    app.include_router(cms_router)
    return TestClient(app)


def _draft(client: TestClient, **over) -> dict:
    body = {"slug": "primera-cronica", "type": "post", "title": "Primera crónica",
            "body": "Texto del cuerpo.", "author": "Don Miguel", **over}
    r = client.post("/cms/content", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_created_content_starts_as_draft_and_is_hidden_from_public(client):
    item = _draft(client)
    assert item["status"] == "draft"
    assert client.get("/cms/content").json() == []  # public list shows nothing yet


def test_publish_makes_it_public_and_fetchable_by_slug(client):
    item = _draft(client)
    pub = client.post(f"/cms/content/{item['id']}/publish")
    assert pub.status_code == 200
    assert pub.json()["status"] == "published"

    listing = client.get("/cms/content").json()
    assert [i["slug"] for i in listing] == ["primera-cronica"]

    got = client.get("/cms/content/primera-cronica")
    assert got.status_code == 200
    assert got.json()["title"] == "Primera crónica"


def test_admin_listing_includes_drafts(client):
    _draft(client)
    assert client.get("/cms/admin/content").json()[0]["status"] == "draft"


def test_update_changes_fields_and_bumps_updated_at(client):
    item = _draft(client)
    r = client.put(f"/cms/content/{item['id']}", json={"title": "Título nuevo"})
    assert r.status_code == 200
    assert r.json()["title"] == "Título nuevo"
    assert r.json()["updated_at"] >= item["updated_at"]


def test_delete_removes_it(client):
    item = _draft(client)
    assert client.delete(f"/cms/content/{item['id']}").status_code == 204
    assert client.get("/cms/admin/content").json() == []


def test_duplicate_slug_is_rejected(client):
    _draft(client)
    r = client.post("/cms/content", json={"slug": "primera-cronica", "type": "post",
                                          "title": "Otra", "body": "x", "author": "a"})
    assert r.status_code == 409


def test_unpublished_slug_is_404_for_public(client):
    _draft(client)  # draft, never published
    assert client.get("/cms/content/primera-cronica").status_code == 404


def test_unknown_id_is_404(client):
    assert client.post("/cms/content/nope/publish").status_code == 404
    assert client.put("/cms/content/nope", json={"title": "x"}).status_code == 404
