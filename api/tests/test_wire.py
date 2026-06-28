"""Tests for the wire projections — the single source of truth for what leaves
the process over SSE. The contract that matters most: tool *input* (which can
carry MCP auth tokens / verbatim queries) NEVER reaches the wire."""

from __future__ import annotations

from types import SimpleNamespace

from app.wire import (
    plan_rejected_to_wire,
    plan_to_wire,
    result_to_wire,
    step_done_to_wire,
    tool_call_to_wire,
)


def test_tool_call_drops_input():
    tc = SimpleNamespace(name="search", server="mcp", id="t1", is_error=False, input={"token": "SECRET"})
    wire = tool_call_to_wire(tc)
    assert wire == {"name": "search", "server": "mcp", "id": "t1", "is_error": False}
    assert "input" not in wire


def test_tool_call_tolerates_partial_object():
    # During the live stream a ToolUseBlock arrives before its result — is_error
    # is still unknown. getattr defaults keep it from raising.
    wire = tool_call_to_wire(SimpleNamespace(name="x"))
    assert wire == {"name": "x", "server": None, "id": None, "is_error": None}


def test_result_to_wire_drops_input_and_fills_session():
    r = SimpleNamespace(
        text="hi",
        tool_calls=[SimpleNamespace(name="t", server=None, id=None, is_error=None, input={"q": "x"})],
        usage={"tokens": 5},
        session_id=None,
    )
    wire = result_to_wire(r, fallback_session_id="sess-1")
    assert wire["text"] == "hi"
    assert wire["session_id"] == "sess-1"
    assert "input" not in wire["tool_calls"][0]


def test_plan_to_wire_coerces_steps_to_strings():
    wire = plan_to_wire({"session_id": "s", "steps": ["a", 2, 3.5, {"drop": "me"}]})
    assert wire == {"session_id": "s", "steps": ["a", "2", "3.5"]}


def test_step_done_normalizes_status():
    assert step_done_to_wire({"step_index": 1, "status": "ok"})["status"] == "done"
    assert step_done_to_wire({"step_index": 1, "status": "failed"})["status"] == "failed"


def test_plan_rejected_keeps_label_drops_regex():
    wire = plan_rejected_to_wire(
        {"reason": "blocked", "guard": "g", "matched": [{"index": 0, "label": "do thing", "pattern": "rm -rf"}]}
    )
    assert wire["matched"] == [{"index": 0, "label": "do thing"}]
    assert "pattern" not in wire["matched"][0]
