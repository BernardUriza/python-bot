import { type AgentStreamEvent } from '@free-intelligence/core';

/**
 * Maps the template api/'s server-side WIRE frame (api/app/wire.py) onto core's
 * `AgentStreamEvent` union. Pure function, no transport — extracted from the hook
 * so it can be unit-tested in isolation. Returns null for frames to drop.
 */
export function mapAgentEvent(ev: Record<string, unknown>): AgentStreamEvent | null {
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
