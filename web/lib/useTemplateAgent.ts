'use client';

/**
 * useTemplateAgent — the template's implementation of core's AgentHook (TRANSPORT).
 *
 * The api/ side (api/app/wire.py + routes/chat.py) already projects fi-runner's
 * native stream onto a server-side WIRE shape. This hook streams that wire shape,
 * maps each frame onto core's `AgentStreamEvent` (via `mapAgentEvent`), and feeds
 * the pure `applyAgentEvent` reducer to build the live turn. The visible transcript
 * is NOT here — fi-glass `useAgentConversation` owns it (the consumer consumes the
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
import { mapAgentEvent } from './agentEventMap';

const SSE_DATA_PREFIX = 'data:';

function authHeaders(): Record<string, string> {
  return API_KEY ? { Authorization: `Bearer ${API_KEY}` } : {};
}

function newSessionId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  return `s-${Date.now()}`;
}

/** Pull the JSON payload out of one SSE frame, or null if it carries no data line. */
function parseSseFrame(frame: string): Record<string, unknown> | null {
  const line = frame.split('\n').find((l) => l.startsWith(SSE_DATA_PREFIX));
  if (!line) return null;
  return JSON.parse(line.slice(SSE_DATA_PREFIX.length).trim());
}

export function useTemplateAgent(): AgentHook {
  const [turn, setTurn] = useState<AgentTurnState>(initialAgentTurnState());
  const [isStreaming, setIsStreaming] = useState(false);
  // One stable client session id for this surface — the api/ requires a non-empty
  // session_id and replays prior turns under it (ConversationStore).
  const sessionIdRef = useRef<string>('');
  if (!sessionIdRef.current) sessionIdRef.current = newSessionId();
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
            const ev = parseSseFrame(frame);
            if (ev) apply(mapAgentEvent(ev));
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
