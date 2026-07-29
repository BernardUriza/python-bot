"""TDD for boot-time CMS seeding — an org's canonical content, in a file,
re-applied on every start so an in-memory store survives a restart.

fi-INDEPENDENT: touches only `app.cms`, never `app.app`.
Run:  python -m pytest tests/test_cms_seed.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.cms.models import ContentDraft
from app.cms.seed import seed_content_store, seed_from_env
from app.cms.store import content_store


@pytest.fixture(autouse=True)
def _clean_store():
    content_store().clear()
    yield
    content_store().clear()


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(payload), encoding="utf8")
    return path


FLAT = {
    "items": [
        {"slug": "una", "title": "Una", "body": "Cuerpo uno.", "author": "Colectiva"},
        {"slug": "dos", "title": "Dos", "body": "Cuerpo dos.", "author": "Colectiva",
         "publish": True},
    ]
}

NESTED = {
    "items": [
        {
            "editorial": {"estatus": "validado", "validado_por": "Alguien"},
            "publish": True,
            "payload": {"slug": "anidada", "title": "Anidada", "body": "Cuerpo.",
                        "author": "Colectiva"},
        }
    ]
}


def test_seeds_drafts_and_publishes_only_the_flagged(tmp_path):
    report = seed_content_store(content_store(), _write(tmp_path, FLAT))

    assert report.created == ["una", "dos"]
    assert report.published == ["dos"]
    assert [i.slug for i in content_store().list(published_only=True)] == ["dos"]
    assert len(content_store().list(published_only=False)) == 2


def test_accepts_the_nested_payload_shape(tmp_path):
    report = seed_content_store(content_store(), _write(tmp_path, NESTED))

    assert report.created == ["anidada"]
    assert report.published == ["anidada"]


def test_is_idempotent_across_restarts(tmp_path):
    path = _write(tmp_path, FLAT)
    seed_content_store(content_store(), path)

    again = seed_content_store(content_store(), path)

    assert again.created == []
    assert again.skipped == ["una", "dos"]
    assert len(content_store().list(published_only=False)) == 2


def test_never_publishes_an_item_it_did_not_create(tmp_path):
    """A slug already in the store is the org's live state — the seeder leaves it
    alone. Otherwise a restart would silently re-publish what someone took down."""
    content_store().create(ContentDraft(slug="dos", title="Dos", body="Cuerpo dos.",
                                        author="Colectiva"))

    report = seed_content_store(content_store(), _write(tmp_path, FLAT))

    assert report.created == ["una"]
    assert report.skipped == ["dos"]
    assert report.published == []
    assert content_store().list(published_only=True) == []


def test_an_item_flagged_skip_is_never_loaded(tmp_path):
    """An org keeps vetoed content in the file as a record of what it decided —
    `skip` says "remember this, never serve it"."""
    path = _write(tmp_path, {"items": [
        {"slug": "vetada", "title": "Vetada", "body": "Cuerpo.", "author": "A", "skip": True},
        {"slug": "viva", "title": "Viva", "body": "Cuerpo.", "author": "A"},
    ]})

    report = seed_content_store(content_store(), path)

    assert report.created == ["viva"]
    assert report.ignored == ["vetada"]
    assert [i.slug for i in content_store().list(published_only=False)] == ["viva"]


def test_a_malformed_item_is_skipped_not_fatal(tmp_path):
    path = _write(tmp_path, {"items": [
        {"slug": "buena", "title": "Buena", "body": "Cuerpo.", "author": "A"},
        {"slug": "mala"},
        {"slug": "otra", "title": "Otra", "body": "Cuerpo.", "author": "A", "extra": "x"},
    ]})

    report = seed_content_store(content_store(), path)

    assert report.created == ["buena"]
    assert report.invalid == ["mala", "otra"]


def test_a_missing_file_warns_and_does_not_crash(tmp_path):
    report = seed_content_store(content_store(), tmp_path / "no-existe.json")

    assert report.created == []
    assert report.error is not None


def test_seed_from_env_is_a_noop_without_the_var(monkeypatch):
    monkeypatch.delenv("CMS_SEED_FILE", raising=False)

    assert seed_from_env(content_store()) is None


def test_seed_from_env_reads_the_configured_path(tmp_path, monkeypatch):
    monkeypatch.setenv("CMS_SEED_FILE", str(_write(tmp_path, FLAT)))

    report = seed_from_env(content_store())

    assert report is not None and report.created == ["una", "dos"]
