"""App-level tests via TestClient: the ungated /health probe and the API-key
gate on /chat/stream. The 401 cases are the regression guard that pairs with the
web client sending the X-API-Key header."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import auth
from app.app import app

client = TestClient(app)

_VALID_BODY = {"session_id": "s1", "message": "hello"}


def test_health_is_ungated_and_ok(monkeypatch):
    # Even with a key configured, /health must answer without one (liveness probe).
    monkeypatch.setattr(auth, "_API_KEY", "s3cret")
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert "version" in body and "uptime_s" in body


def test_chat_stream_401_without_key_when_configured(monkeypatch):
    monkeypatch.setattr(auth, "_API_KEY", "s3cret")
    res = client.post("/chat/stream", json=_VALID_BODY)
    assert res.status_code == 401


def test_chat_stream_401_with_wrong_key(monkeypatch):
    monkeypatch.setattr(auth, "_API_KEY", "s3cret")
    res = client.post("/chat/stream", json=_VALID_BODY, headers={"X-API-Key": "nope"})
    assert res.status_code == 401


def test_chat_stream_rejects_extra_fields(monkeypatch):
    # ChatRequest forbids extras — a typo'd field is a 422, not silently ignored.
    monkeypatch.setattr(auth, "_API_KEY", None)
    res = client.post("/chat/stream", json={**_VALID_BODY, "bogus": 1})
    assert res.status_code == 422
