"""Tests for the API-key gate — the floor that stops a crawler that finds the
public Container App URL from draining the agent budget. The header NAME matters:
the web client must send the same one this dependency reads (regression guard for
the X-API-Key vs Authorization mismatch)."""

from __future__ import annotations

import inspect

import pytest
from fastapi import HTTPException

from app import auth


@pytest.mark.asyncio
async def test_fail_open_when_no_key_configured(monkeypatch):
    monkeypatch.setattr(auth, "_API_KEY", None)
    # No raise == allowed.
    assert await auth.verify_api_key("anything") is None
    assert await auth.verify_api_key(None) is None


@pytest.mark.asyncio
async def test_rejects_missing_key_when_configured(monkeypatch):
    monkeypatch.setattr(auth, "_API_KEY", "s3cret")
    with pytest.raises(HTTPException) as exc:
        await auth.verify_api_key(None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_rejects_wrong_key(monkeypatch):
    monkeypatch.setattr(auth, "_API_KEY", "s3cret")
    with pytest.raises(HTTPException) as exc:
        await auth.verify_api_key("nope")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_accepts_correct_key(monkeypatch):
    monkeypatch.setattr(auth, "_API_KEY", "s3cret")
    assert await auth.verify_api_key("s3cret") is None
    # whitespace is tolerated (clients/proxies sometimes pad headers)
    assert await auth.verify_api_key("  s3cret  ") is None


def test_gate_reads_the_x_api_key_header():
    """The dependency binds to the `x_api_key` parameter → `X-API-Key` header.
    The web client (web/lib/api.ts apiHeaders) MUST send that exact header."""
    sig = inspect.signature(auth.verify_api_key)
    assert "x_api_key" in sig.parameters
