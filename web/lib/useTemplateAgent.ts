'use client';

/**
 * useTemplateAgent — the template's implementation of core's AgentHook (TRANSPORT).
 *
 * The api/ side (api/app/wire.py + routes/chat.py) already projects fi-runner's
 * native stream onto a server-side WIRE shape. This hook does the thin remap from
 * that wire shape onto core's `AgentStreamEvent` union, then feeds the pure
 * `applyAgentEvent` reducer to build the live turn. The visible transcript is NOT
 * here — fi-glass `useAgentConversation` owns it (the consumer consumes the
 * primitive; it does not re-implement it).
 *
 * Modelled on apps/og118/web/lib/useOg118Agent.ts. The template is unauthenticated
 * by default and owns a single client-side session id (no conversation library).
 */

import { useCallback, useRef, useState } from 'react';
import {
  applyAgentEvent,
  initialAgentTurnState,
  type AgentHook,
  type AgentStreamEvent,
  type AgentTurnState,
} from '@free-intelligence/core';
import { API_URL, API_KEY } from './api';

/** Template server WIRE frame → core AgentStreamEvent (or null to drop). */
function mapEvent(ev: Record<string, unknown>): AgentStreamEvent | null {
  switch (ev.type) {
    case 'open':
      return {
        type: 'open',
        sessionId: (ev.session_id as string | undefined) ?? undefined,
        requestId: (ev.request_id as string | undefined) ?? undefined,
      };
    case 'text':
      return { type: 'text', delta: String(ev.delta ?? '') };
    case 'tool_call':
      return {
        type: 'tool_call',
        call: {
          id: (ev.id as string | null) ?? null,
          name: String(ev.name ?? ''),
          server: (ev.server as string | null) ?? null,
          isError: (ev.is_error as boolean | null) ?? null,
        },
      };
    case 'plan':
      return { type: 'plan', steps: ((ev.steps as string[]) ?? []).map(String) };
    case 'plan_rejected':
      return {
        type: 'plan_rejected',
        rejection: {
          reason: String(ev.reason ?? ''),
          matched: (ev.matched as Array<{ index: number; label: string }>) ?? [],
          guard: (ev.guard as string | null) ?? null,
        },
      };
    case 'step_started':
      return { type: 'step_started', index: Number(ev.step_index ?? -1) };
    case 'step_done':
      return {
        type: 'step_done',
        index: Number(ev.step_index ?? -1),
        status: ev.status === 'failed' ? 'failed' : 'done',
        summary: ev.summary ? String(ev.summary) : undefined,
        error: ev.error ? String(ev.error) : undefined,
      };
    case 'result':
      return { type: 'result', text: String(ev.text ?? '') };
    case 'error':
      return { type: 'error', message: String(ev.message ?? 'error') };
    case 'done':
      return { type: 'done' };
    default:
      return null;
  }
}

function authHeaders(): Record<string, string> {
  return API_KEY ? { Authorization: `Bearer ${API_KEY}` } : {};
}

export function useTemplateAgent(): AgentHook {
  const [turn, setTurn] = useState<AgentTurnState>(initialAgentTurnState());
  const [isStreaming, setIsStreaming] = useState(false);
  // One stable client session id for this surface — the api/ requires a non-empty
  // session_id and replays prior turns under it (ConversationStore).
  const sessionIdRef = useRef<string>('');
  if (!sessionIdRef.current) {
    sessionIdRef.current =
      typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `s-${Date.now()}`;
  }
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (message: string) => {
      const text = message.trim();
      if (!text || isStreaming) return;

      let state = initialAgentTurnState();
      setTurn(state);
      setIsStreaming(true);
      const apply = (core: AgentStreamEvent | null) => {
        if (!core) return;
        state = applyAgentEvent(state, core);
        setTurn(state);
      };

      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const res = await fetch(`${API_URL}/chat/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authHeaders() },
          body: JSON.stringify({ message: text, session_id: sessionIdRef.current }),
          signal: controller.signal,
        });
        if (!res.body) throw new Error('no response body');
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const frames = buffer.split('\n\n');
          buffer = frames.pop() ?? '';
          for (const frame of frames) {
            const line = frame.split('\n').find((l) => l.startsWith('data:'));
            if (!line) continue;
            apply(mapEvent(JSON.parse(line.slice(5).trim())));
          }
        }
      } catch (err) {
        if (!(err instanceof DOMException && err.name === 'AbortError')) {
          apply({ type: 'error', message: err instanceof Error ? err.message : String(err) });
        }
      } finally {
        abortRef.current = null;
        setIsStreaming(false);
      }
    },
    [isStreaming],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    setTurn(initialAgentTurnState());
  }, []);

  return { turn, isStreaming, send, reset, abort };
}
