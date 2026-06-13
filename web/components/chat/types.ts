/** Wire types for the /chat/stream SSE feed and the in-memory chat model.
 *
 * Keep this file pure data — no React, no fetch. It MIRRORS the API wire shape
 * (see api/app/wire.py). When that file changes, this one changes with it. */

/** One tool call surfaced as a "thinking step". Mirrors ToolCallWire — the
 * tool `input` is dropped on purpose (token-safe). */
export type Step = {
  id: string | null;
  /** raw tool name, e.g. `mcp__fetch__get` or `Bash`. */
  name: string;
  /** MCP server name or null for built-ins. */
  server: string | null;
  /** known result status; `null` = still running / unknown. */
  isError: boolean | null;
};

/** One step inside the agent's declared plan. Mirrors PlanWire/StepStartedWire/
 * StepDoneWire plus a client-side `status` composed from the SSE event sequence.
 * Status machine: pending → running (step_started) → done | failed (step_done). */
export type PlanStep = {
  label: string;
  status: "pending" | "running" | "done" | "failed";
  summary?: string;
  error?: string;
};

/** A pre-execution rejection from fi-runner's PlanGuard. SOFT — the stream
 * keeps going; the agent's retry path re-declares. Surfaced so a viewer sees
 * the guardrail catch an off-policy plan. */
export type PlanRejection = {
  reason: string;
  matched: Array<{ index: number; label: string }>;
  guard: string | null;
};

export type Plan = {
  steps: PlanStep[];
  rejection?: PlanRejection | null;
};

/** Per-turn observability — fi_runner's `turn_completed` projected to the wire
 * (see api/app/routes/chat.py meta event). Shown as a small footer. */
export type ChatMeta = {
  request_id?: string | null;
  latency_ms?: number | null;
  tool_count?: number | null;
  tokens?: Record<string, unknown> | null;
  attempts?: number | null;
  model?: string | null;
  replayed_messages?: number | null;
};

export type ChatMessage =
  | { id: string; role: "user"; content: string }
  | {
      id: string;
      role: "assistant";
      /** Live text accumulated from `text` events. Replaced wholesale on the
       * `result` event (post-guard text may differ — antidrift can rewrite). */
      content: string;
      steps: Step[];
      /** Null until the agent's first `declare_plan` lands. Stays null on
       * backends that don't capture MCP inputs (codex). */
      plan: Plan | null;
      usage: Record<string, unknown> | null;
      meta: ChatMeta | null;
      status: "thinking" | "streaming" | "done" | "error";
      errorMessage?: string;
    };
