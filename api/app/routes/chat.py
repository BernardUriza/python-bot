"""POST /chat/stream — multi-turn chat with live chain-of-thought as SSE."""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ..auth import limiter, verify_api_key
from ..models import ChatRequest
from ..observability import current_request_id
from ..runner import chat_stream
from ..validation import (
    CHAT_TURN_TIMEOUT_S,
    REQUEST_TEXT_MAX_CHARS,
    SSE_HEARTBEAT_S,
    clean_optional_id,
    clean_text,
    public_error_message,
    validate_backend,
)
from ..wire import (
    plan_rejected_to_wire,
    plan_to_wire,
    result_to_wire,
    step_done_to_wire,
    step_started_to_wire,
    tool_call_to_wire,
)

_log = logging.getLogger("app.routes.chat")

router = APIRouter()


def _sse(event: str, data: dict) -> str:
    """Format one SSE message. Newlines in `data` are JSON-escaped so a
    single 'data:' line is always valid per the SSE spec."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# SSE comment frame — no `event:`/`data:` line, so the client's parser returns
# null and skips it. Pure connection keepalive.
_SSE_HEARTBEAT = ": keepalive\n\n"


async def _with_heartbeat(
    aiter: AsyncIterator[dict],
    *,
    interval: float,
) -> AsyncIterator[tuple[str, dict | None]]:
    """Yield ``("event", item)`` for each item from ``aiter``, plus
    ``("beat", None)`` whenever ``interval`` seconds elapse with no item.

    The agent goes silent between its last tool call and the first text delta
    (composing — no bytes on the wire). Without a keepalive an idle
    proxy/ingress resets the connection and the browser surfaces "network
    error" mid-turn. A background pump decouples producing events from the
    heartbeat clock; upstream exceptions are re-raised in-band so the caller's
    error handling is unchanged.
    """
    queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()

    async def _pump() -> None:
        try:
            async for item in aiter:
                await queue.put(("event", item))
            await queue.put(("done", None))
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - relayed to the consumer below
            await queue.put(("error", exc))

    task = asyncio.create_task(_pump())
    try:
        while True:
            try:
                kind, payload = await asyncio.wait_for(queue.get(), timeout=interval)
            except TimeoutError:
                yield ("beat", None)
                continue
            if kind == "event":
                yield ("event", payload)  # type: ignore[arg-type]
            elif kind == "error":
                raise payload  # type: ignore[misc]
            else:  # "done"
                return
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


@router.post("/chat/stream", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/hour")
async def chat_stream_endpoint(request: Request, req: ChatRequest) -> StreamingResponse:
    """Multi-turn chat with live chain-of-thought as Server-Sent Events.

    Re-emits each event from ``runner.chat_stream`` as SSE so the UI can paint
    every tool call as a step while the text streams token by token. Live
    streaming requires the claude backend; codex falls back to a single
    ``result`` event (per fi-runner).

    Wire contract (event → payload):
      open          {"session_id","request_id"}
      plan          PlanWire                 (declare_plan)
      plan_rejected PlanRejectedWire         (PlanGuard veto — soft, stream continues)
      step_started  StepStartedWire          (start_step → row goes "running")
      step_done     StepDoneWire             (complete_step | fail_step)
      tool_call     ToolCallWire             (no input — token-safe)
      text          {"delta"}               (token-ish chunk)
      result        ResultWire
      meta          {...}                    (closing telemetry)
      error         {"message","kind"}
      done          {}                       (always fires last, even after error)
    """
    session_id = req.session_id  # already validated by Pydantic Field constraints
    request_id = current_request_id()
    message = clean_text(req.message, field="message", max_chars=REQUEST_TEXT_MAX_CHARS)
    backend = validate_backend(req.backend)
    corpus_id = clean_optional_id(req.corpus_id, field="corpus_id")

    # Per-turn telemetry capture. Lives in closure so each request gets its own
    # list (no cross-request leak).
    captured: list[tuple[str, dict]] = []
    t0 = time.perf_counter()

    def _on_event(event: str, fields: dict) -> None:
        captured.append((event, fields))
        if event in ("backend_error", "guard_failed", "plan_rejected"):
            _log.warning("chat.event %s detail=%s", event, fields)
        else:
            _log.info(
                "chat.event %s",
                event,
                extra={"event": event, "session_id": session_id, "fields": fields},
            )

    async def gen():
        # Tell the client the stream is live so the UI flips 'thinking…' on
        # before the first tool_call lands.
        yield _sse("open", {"session_id": session_id, "request_id": request_id})
        try:
            async with asyncio.timeout(CHAT_TURN_TIMEOUT_S):
                stream = chat_stream(
                    message,
                    session_id=session_id,
                    backend=backend,
                    corpus_id=corpus_id,
                    on_event=_on_event,
                )
                async for kind, event in _with_heartbeat(stream, interval=SSE_HEARTBEAT_S):
                    if kind == "beat" or event is None:
                        # Keeps an idle proxy/ingress from resetting the socket
                        # during the model's silent think-then-compose gap.
                        yield _SSE_HEARTBEAT
                        continue
                    etype = event.get("type")
                    if etype == "tool_call":
                        yield _sse("tool_call", dict(tool_call_to_wire(event["tool"])))
                    elif etype == "text":
                        yield _sse("text", {"delta": event["text"]})
                    elif etype == "plan":
                        yield _sse("plan", dict(plan_to_wire(event["data"])))
                    elif etype == "plan_rejected":
                        yield _sse("plan_rejected", dict(plan_rejected_to_wire(event["data"])))
                    elif etype == "step_started":
                        yield _sse("step_started", dict(step_started_to_wire(event["data"])))
                    elif etype == "step_done":
                        yield _sse("step_done", dict(step_done_to_wire(event["data"])))
                    elif etype == "result":
                        # UI MUST REPLACE, not append — antidrift may have
                        # rewritten the live deltas.
                        payload = result_to_wire(event["result"], fallback_session_id=session_id)
                        yield _sse("result", dict(payload))

            # Turn settled — emit closing telemetry as `meta`.
            tc = next((f for e, f in captured if e == "turn_completed"), None)
            replayed = next((f for e, f in captured if e == "history_replayed"), None)
            yield _sse("meta", {
                "request_id": request_id,
                "latency_ms": (tc or {}).get("latency_ms", round((time.perf_counter() - t0) * 1000, 2)),
                "tool_count": (tc or {}).get("tool_count"),
                "tokens": (tc or {}).get("tokens"),
                "attempts": (tc or {}).get("attempts"),
                "model": (tc or {}).get("model"),
                "replayed_messages": (replayed or {}).get("messages", 0),
            })
        except asyncio.CancelledError:
            # Client closed the tab — propagate so the backend SDK request
            # actually cancels instead of burning tokens in the shadow.
            raise
        except TimeoutError as exc:
            _log.error("chat turn exceeded %ss timeout (session=%s)", CHAT_TURN_TIMEOUT_S, session_id)
            yield _sse("error", {"message": public_error_message(exc), "kind": "TimeoutError"})
        except Exception as exc:  # noqa: BLE001 - boundary: surface to UI
            _log.exception("chat turn failed (session=%s)", session_id)
            yield _sse("error", {"message": public_error_message(exc), "kind": type(exc).__name__})
        finally:
            yield _sse("done", {})

    # X-Accel-Buffering: no disables nginx/proxy buffering so events arrive in
    # real time. Connection: keep-alive keeps the SSE socket open on
    # hop-by-hop proxies.
    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
