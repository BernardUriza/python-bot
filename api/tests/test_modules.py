"""TDD for the opt-in module selector. Pure env parsing — no fi_runner."""
from __future__ import annotations

from app.modules import enabled_optional_modules


def test_empty_when_unset(monkeypatch):
    monkeypatch.delenv("APP_MODULES", raising=False)
    assert enabled_optional_modules() == set()


def test_parses_comma_list_normalized(monkeypatch):
    monkeypatch.setenv("APP_MODULES", " CMS , marketplace ,")
    assert enabled_optional_modules() == {"cms", "marketplace"}


def test_blank_is_empty(monkeypatch):
    monkeypatch.setenv("APP_MODULES", "   ")
    assert enabled_optional_modules() == set()
