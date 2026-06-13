"use client";

import type { Plan, Step } from "./types";

/** Live chain-of-thought: the agent's declared plan (ticked as steps land) and
 * the raw tool calls. Both are derived from SSE events (see useChat). */
export function ThinkingPanel({ plan, steps }: { plan: Plan | null; steps: Step[] }) {
  if (!plan && steps.length === 0) return null;

  return (
    <div className="mb-2 rounded-lg border border-app-border bg-app-surface/40 p-3 text-sm">
      {plan && (
        <ol className="space-y-1.5">
          {plan.steps.map((s, i) => (
            <li key={i} className="flex items-start gap-2">
              <span aria-hidden className="mt-0.5 w-4 shrink-0 text-center">
                {s.status === "done" ? "✓" : s.status === "failed" ? "✕" : s.status === "running" ? "▸" : "·"}
              </span>
              <span className={s.status === "failed" ? "text-amber-400" : "text-zinc-200"}>
                {s.label}
                {s.summary && <span className="block text-xs text-app-muted">{s.summary}</span>}
                {s.error && <span className="block text-xs text-amber-400">{s.error}</span>}
              </span>
            </li>
          ))}
        </ol>
      )}
      {plan?.rejection && (
        <p className="mt-2 rounded border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-xs text-amber-300">
          PlanGuard: {plan.rejection.reason}
        </p>
      )}
      {steps.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {steps.map((s, i) => (
            <span
              key={s.id ?? i}
              className={`rounded px-1.5 py-0.5 font-mono text-[11px] ${
                s.isError ? "bg-amber-500/15 text-amber-300" : "bg-app-bg text-app-muted"
              }`}
              title={s.server ?? undefined}
            >
              {s.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
