"""Tests for the SSE plumbing in routes/chat.py: frame formatting and the
heartbeat pump that keeps an idle proxy from resetting the socket during the
model's silent think-then-compose gap."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import pytest

from app.routes.chat import _SSE_HEARTBEAT, _sse, _with_heartbeat


def test_sse_formats_event_and_data_lines():
    frame = _sse("text", {"delta": "hi\nthere"})
    assert frame.startswith("event: text\ndata: ")
    assert frame.endswith("\n\n")
    # newline in the payload is JSON-escaped → still a single data: line
    assert frame.count("\ndata:") == 1
    payload = json.loads(frame.split("data: ", 1)[1].strip())
    assert payload == {"delta": "hi\nthere"}


def test_heartbeat_frame_is_a_bare_comment():
    assert _SSE_HEARTBEAT == ": keepalive\n\n"


async def _aiter(items: list[dict], *, delay: float = 0.0) -> AsyncIterator[dict]:
    for it in items:
        if delay:
            await asyncio.sleep(delay)
        yield it


@pytest.mark.asyncio
async def test_with_heartbeat_relays_events_then_stops():
    out = [kind async for kind, _ in _with_heartbeat(_aiter([{"a": 1}, {"b": 2}]), interval=10)]
    assert out == ["event", "event"]


@pytest.mark.asyncio
async def test_with_heartbeat_emits_beat_on_idle():
    # Source is slower than the interval → at least one beat before the event.
    kinds = []
    async for kind, _ in _with_heartbeat(_aiter([{"x": 1}], delay=0.05), interval=0.01):
        kinds.append(kind)
    assert "beat" in kinds
    assert kinds[-1] == "event"


@pytest.mark.asyncio
async def test_with_heartbeat_relays_upstream_exception():
    async def _boom() -> AsyncIterator[dict]:
        yield {"ok": 1}
        raise RuntimeError("upstream failed")

    seen = []
    with pytest.raises(RuntimeError, match="upstream failed"):
        async for kind, payload in _with_heartbeat(_boom(), interval=10):
            seen.append((kind, payload))
    assert seen == [("event", {"ok": 1})]
