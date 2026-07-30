"""TDD for boot-time seeding — an org's canonical catalogue, in a file, re-applied
on every start so an in-memory store survives a restart.

ONE seeder serves CMS and marketplace; every test runs through BOTH, so a change
that only fits one module fails here. fi-INDEPENDENT: touches only the
pure-pydantic halves, never `app.app`.
Run:  python -m pytest tests/test_seeding.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.cms.models import ContentDraft
from app.cms.store import content_store
from app.marketplace.models import ProductDraft
from app.marketplace.store import product_store
from app.seeding import seed_from_env, seed_store


def _cms_draft(slug: str, **over) -> dict:
    return {"slug": slug, "title": slug.title(), "body": "Cuerpo.",
            "author": "Colectiva", **over}


def _mkt_draft(slug: str, **over) -> dict:
    return {"slug": slug, "title": slug.title(), "description": "Pieza única.",
            "price_cents": 35000, "currency": "MXN", "stock": 2,
            "seller": "Puesto", **over}


MODULES = [
    ("cms", content_store, ContentDraft, _cms_draft),
    ("marketplace", product_store, ProductDraft, _mkt_draft),
]
IDS = [m[0] for m in MODULES]
BOTH = pytest.mark.parametrize("name,store,model,draft", MODULES, ids=IDS)


@pytest.fixture(autouse=True)
def _clean_stores():
    content_store().clear()
    product_store().clear()
    yield
    content_store().clear()
    product_store().clear()


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(payload), encoding="utf8")
    return path


@BOTH
def test_seeds_and_publishes_only_the_flagged(tmp_path, name, store, model, draft):
    path = _write(tmp_path, {"items": [draft("una"), {**draft("dos"), "publish": True}]})

    report = seed_store(store(), path, model)

    assert report.created == ["una", "dos"]
    assert report.published == ["dos"]
    assert [i.slug for i in store().list(published_only=True)] == ["dos"]
    assert len(store().list(published_only=False)) == 2


@BOTH
def test_accepts_the_nested_payload_shape(tmp_path, name, store, model, draft):
    path = _write(tmp_path, {"items": [
        {"editorial": {"aprobado_por": "Alguien"}, "publish": True, "payload": draft("anidada")},
    ]})

    report = seed_store(store(), path, model)

    assert report.created == ["anidada"]
    assert report.published == ["anidada"]


@BOTH
def test_is_idempotent_across_restarts(tmp_path, name, store, model, draft):
    path = _write(tmp_path, {"items": [draft("una"), {**draft("dos"), "publish": True}]})
    seed_store(store(), path, model)

    again = seed_store(store(), path, model)

    assert again.created == []
    assert again.skipped == ["una", "dos"]
    assert len(store().list(published_only=False)) == 2


@BOTH
def test_never_publishes_an_item_it_did_not_create(tmp_path, name, store, model, draft):
    """A slug already in the store is the org's live state — the seeder leaves it
    alone. Otherwise a restart would silently re-publish what someone took down."""
    store().create(model(**draft("dos")))
    path = _write(tmp_path, {"items": [draft("una"), {**draft("dos"), "publish": True}]})

    report = seed_store(store(), path, model)

    assert report.created == ["una"]
    assert report.skipped == ["dos"]
    assert report.published == []
    assert store().list(published_only=True) == []


@BOTH
def test_an_item_flagged_skip_is_never_loaded(tmp_path, name, store, model, draft):
    """An org keeps vetoed items in the file as a record of what it decided —
    `skip` says "remember this, never serve it"."""
    path = _write(tmp_path, {"items": [{**draft("vetada"), "skip": True}, draft("viva")]})

    report = seed_store(store(), path, model)

    assert report.created == ["viva"]
    assert report.ignored == ["vetada"]
    assert [i.slug for i in store().list(published_only=False)] == ["viva"]


@BOTH
def test_a_malformed_item_is_skipped_not_fatal(tmp_path, name, store, model, draft):
    path = _write(tmp_path, {"items": [
        draft("buena"),
        {"slug": "mala"},
        {**draft("otra"), "campo_inventado": "x"},
    ]})

    report = seed_store(store(), path, model)

    assert report.created == ["buena"]
    assert report.invalid == ["mala", "otra"]


@BOTH
def test_a_missing_file_warns_and_does_not_crash(tmp_path, name, store, model, draft):
    report = seed_store(store(), tmp_path / "no-existe.json", model)

    assert report.created == []
    assert report.error is not None


@BOTH
def test_seed_from_env_is_a_noop_without_the_var(monkeypatch, name, store, model, draft):
    monkeypatch.delenv("UNA_VAR_DE_SEED", raising=False)

    assert seed_from_env(store(), model, "UNA_VAR_DE_SEED") is None


@BOTH
def test_seed_from_env_reads_the_configured_path(tmp_path, monkeypatch, name, store, model, draft):
    monkeypatch.setenv("UNA_VAR_DE_SEED", str(_write(tmp_path, {"items": [draft("una"), draft("dos")]})))

    report = seed_from_env(store(), model, "UNA_VAR_DE_SEED")

    assert report is not None and report.created == ["una", "dos"]
