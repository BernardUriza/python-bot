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
import { API_URL, CHAT_STREAM_TIMEOUT_MS, apiHeaders } from './api';
import { mapAgentEvent } from './agentEventMap';
import { loadOrCreateSessionId, rotateSessionId } from './session';

const SSE_DATA_PREFIX = 'data:';

/** Pull the JSON payload out of one SSE frame, or null if it carries no data line. */
function parseSseFrame(frame: string): Record<string, unknown> | null {
  const line = frame.split('\n').find((l) => l.startsWith(SSE_DATA_PREFIX));
  if (!line) return null;
  return JSON.parse(line.slice(SSE_DATA_PREFIX.length).trim());
}

export function useTemplateAgent(): AgentHook {
  const [turn, setTurn] = useState<AgentTurnState>(initialAgentTurnState());
  const [isStreaming, setIsStreaming] = useState(false);
  // One stable, PERSISTED session id for this surface — the api/ requires a
  // non-empty session_id and replays prior turns under it (ConversationStore),
  // so persisting it across reloads is what makes that longitudinal memory
  // actually reach the user.
  const sessionIdRef = useRef<string>('');
  if (!sessionIdRef.current) sessionIdRef.current = loadOrCreateSessionId();
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
      // Client-side watchdog: a wedged stream (proxy ate the heartbeat, server
      // hung) must not hang the UI forever. Kept LONGER than the server turn
      // timeout so the server wins the race and returns its own error first;
      // this only fires if the server never responds at all. Tagged
      // TimeoutError (not AbortError) so it surfaces to the user instead of
      // being swallowed like a manual cancel.
      const watchdog = setTimeout(
        () => controller.abort(new DOMException('stream timed out', 'TimeoutError')),
        CHAT_STREAM_TIMEOUT_MS,
      );
      try {
        const res = await fetch(`${API_URL}/chat/stream`, {
          method: 'POST',
          headers: apiHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ message: text, session_id: sessionIdRef.current }),
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`chat request failed (${res.status})`);
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
        // A manual abort (user hit stop) is silent; a timeout / real failure surfaces.
        if (!(err instanceof DOMException && err.name === 'AbortError')) {
          apply({ type: 'error', message: err instanceof Error ? err.message : String(err) });
        }
      } finally {
        clearTimeout(watchdog);
        abortRef.current = null;
        setIsStreaming(false);
      }
    },
    [isStreaming],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  // reset() backs fi-glass's built-in "New Chat" button. Beyond clearing the
  // visible turn, we ROTATE the persisted session id so a new conversation
  // truly starts fresh — otherwise the backend ConversationStore would keep
  // replaying the old thread under the same id.
  const reset = useCallback(() => {
    sessionIdRef.current = rotateSessionId();
    setTurn(initialAgentTurnState());
  }, []);

  return { turn, isStreaming, send, reset, abort };
}
