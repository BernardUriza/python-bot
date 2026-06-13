"use client";

import { useCallback, useRef, useState } from "react";
import { CHAT_STREAM_TIMEOUT_MS, apiHeaders, apiUrl } from "../../lib/api";
import { newId } from "../../lib/id";
import { parseSseFrame } from "../../lib/sse";
import type { ChatMeta, ChatMessage, PlanStep, Step } from "./types";

/** Drive the /chat/stream SSE feed: append the user turn, stream the agent's
 * chain-of-thought (plan → steps → tool calls → text → result), and keep the
 * in-memory thread. The backend's ConversationStore owns history replay — the
 * client only sends the latest message plus a stable session_id. */
export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const sessionIdRef = useRef<string>(newId());
  const abortRef = useRef<AbortController | null>(null);

  const patchAssistant = useCallback(
    (id: string, patch: (m: Extract<ChatMessage, { role: "assistant" }>) => Extract<ChatMessage, { role: "assistant" }>) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === id && m.role === "assistant" ? patch(m) : m)),
      );
    },
    [],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || streaming) return;

      const userMsg: ChatMessage = { id: newId(), role: "user", content: trimmed };
      const assistantId = newId();
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        steps: [],
        plan: null,
        usage: null,
        meta: null,
        status: "thinking",
      };
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;
      const timeout = window.setTimeout(() => controller.abort(), CHAT_STREAM_TIMEOUT_MS);

      try {
        const res = await fetch(apiUrl("/chat/stream"), {
          method: "POST",
          headers: apiHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify({ session_id: sessionIdRef.current, message: trimmed }),
          signal: controller.signal,
        });
        if (!res.ok || !res.body) {
          throw new Error(`HTTP ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          // SSE frames are separated by a blank line.
          const frames = buffer.split("\n\n");
          buffer = frames.pop() ?? "";
          for (const frame of frames) {
            const parsed = parseSseFrame(frame);
            if (!parsed) continue;
            handleEvent(assistantId, parsed.event, parsed.data, patchAssistant);
          }
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        patchAssistant(assistantId, (m) => ({
          ...m,
          status: "error",
          errorMessage: message,
        }));
      } finally {
        window.clearTimeout(timeout);
        abortRef.current = null;
        setStreaming(false);
        patchAssistant(assistantId, (m) =>
          m.status === "thinking" || m.status === "streaming" ? { ...m, status: "done" } : m,
        );
      }
    },
    [streaming, patchAssistant],
  );

  return { messages, streaming, send, abort, sessionId: sessionIdRef.current };
}

type Patch = (
  id: string,
  patch: (m: Extract<ChatMessage, { role: "assistant" }>) => Extract<ChatMessage, { role: "assistant" }>,
) => void;

function handleEvent(id: string, event: string, data: unknown, patch: Patch) {
  const d = (data ?? {}) as Record<string, unknown>;
  switch (event) {
    case "plan": {
      const steps: PlanStep[] = ((d.steps as string[]) ?? []).map((label) => ({
        label,
        status: "pending",
      }));
      patch(id, (m) => ({ ...m, plan: { steps, rejection: null } }));
      break;
    }
    case "plan_rejected": {
      patch(id, (m) => ({
        ...m,
        plan: {
          steps: m.plan?.steps ?? [],
          rejection: {
            reason: String(d.reason ?? "plan rejected"),
            matched: (d.matched as Array<{ index: number; label: string }>) ?? [],
            guard: (d.guard as string | null) ?? null,
          },
        },
      }));
      break;
    }
    case "step_started": {
      const idx = Number(d.step_index ?? 0);
      patch(id, (m) => withStepStatus(m, idx, "running"));
      break;
    }
    case "step_done": {
      const idx = Number(d.step_index ?? 0);
      const status = d.status === "failed" ? "failed" : "done";
      patch(id, (m) =>
        withStepStatus(m, idx, status, {
          summary: d.summary as string | undefined,
          error: d.error as string | undefined,
        }),
      );
      break;
    }
    case "tool_call": {
      const step: Step = {
        id: (d.id as string | null) ?? null,
        name: String(d.name ?? "tool"),
        server: (d.server as string | null) ?? null,
        isError: (d.is_error as boolean | null) ?? null,
      };
      patch(id, (m) => ({ ...m, status: "streaming", steps: [...m.steps, step] }));
      break;
    }
    case "text": {
      const delta = String(d.delta ?? "");
      patch(id, (m) => ({ ...m, status: "streaming", content: m.content + delta }));
      break;
    }
    case "result": {
      patch(id, (m) => ({
        ...m,
        content: String(d.text ?? m.content),
        usage: (d.usage as Record<string, unknown> | null) ?? null,
        status: "done",
      }));
      break;
    }
    case "meta": {
      patch(id, (m) => ({ ...m, meta: d as ChatMeta }));
      break;
    }
    case "error": {
      patch(id, (m) => ({
        ...m,
        status: "error",
        errorMessage: String(d.message ?? "request failed"),
      }));
      break;
    }
    default:
      break;
  }
}

function withStepStatus(
  m: Extract<ChatMessage, { role: "assistant" }>,
  index: number,
  status: PlanStep["status"],
  extra?: { summary?: string; error?: string },
): Extract<ChatMessage, { role: "assistant" }> {
  if (!m.plan) return m;
  const steps = m.plan.steps.map((s, i) =>
    i === index ? { ...s, status, ...(extra ?? {}) } : s,
  );
  return { ...m, plan: { ...m.plan, steps } };
}
