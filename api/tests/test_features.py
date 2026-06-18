"""TDD for the feature-flag system — the SSOT that composes an app from a
declared subset of capabilities. Pure (env + registry), fi-INDEPENDENT.

Contract:
  - the core feature (chat) is ALWAYS enabled, even when APP_MODULES is unset;
  - declaring a feature auto-enables its `requires` (transitive);
  - unknown keys are dropped (forgiving), never crash the boot;
  - parsing is comma-separated, case-insensitive, whitespace-tolerant.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features import CORE_FEATURES, feature_router, resolve_features


def test_core_always_on_even_when_unset():
    assert resolve_features(None) == set(CORE_FEATURES)
    assert resolve_features("") == set(CORE_FEATURES)


def test_declared_features_added_to_core():
    assert resolve_features("cms,marketplace") == {*CORE_FEATURES, "cms", "marketplace"}


def test_parsing_is_case_insensitive_and_trimmed():
    assert resolve_features("  CMS , Marketplace ,") == {*CORE_FEATURES, "cms", "marketplace"}


def test_unknown_keys_are_dropped_not_crashing():
    assert resolve_features("cms,banana") == {*CORE_FEATURES, "cms"}


def test_requires_are_expanded_transitively(monkeypatch):
    # register a synthetic feature that requires cms to prove dep expansion
    from app import features as F
    monkeypatch.setitem(F.FEATURES, "blog", F.Feature(key="blog", label="Blog", requires=("cms",)))
    assert resolve_features("blog") == {*CORE_FEATURES, "blog", "cms"}


def test_features_endpoint_reports_enabled(monkeypatch):
    monkeypatch.setenv("APP_MODULES", "cms")
    app = FastAPI()
    app.include_router(feature_router)
    body = TestClient(app).get("/features").json()
    assert body["enabled"] == sorted({*CORE_FEATURES, "cms"})
    assert body["features"]["cms"]["enabled"] is True
    assert body["features"]["marketplace"]["enabled"] is False
