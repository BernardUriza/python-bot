import { describe, it, expect } from 'vitest';
import { mapAgentEvent } from './agentEventMap';

describe('mapAgentEvent — template wire frame → core AgentStreamEvent', () => {
  it('maps open, renaming snake_case → camelCase', () => {
    expect(mapAgentEvent({ type: 'open', session_id: 's1', request_id: 'r1' })).toEqual({
      type: 'open',
      sessionId: 's1',
      requestId: 'r1',
    });
  });

  it('maps text to a delta', () => {
    expect(mapAgentEvent({ type: 'text', delta: 'hi' })).toEqual({ type: 'text', delta: 'hi' });
    expect(mapAgentEvent({ type: 'text' })).toEqual({ type: 'text', delta: '' });
  });

  it('maps tool_call, renaming is_error → isError', () => {
    expect(
      mapAgentEvent({ type: 'tool_call', id: 't1', name: 'search', server: 'mcp', is_error: true }),
    ).toEqual({
      type: 'tool_call',
      call: { id: 't1', name: 'search', server: 'mcp', isError: true },
    });
  });

  it('defaults a tool_call with no error flag to isError null', () => {
    const ev = mapAgentEvent({ type: 'tool_call', name: 'x' });
    expect(ev).toMatchObject({ type: 'tool_call', call: { isError: null, id: null, server: null } });
  });

  it('maps plan steps to strings', () => {
    expect(mapAgentEvent({ type: 'plan', steps: ['a', 'b'] })).toEqual({
      type: 'plan',
      steps: ['a', 'b'],
    });
    expect(mapAgentEvent({ type: 'plan' })).toEqual({ type: 'plan', steps: [] });
  });

  it('maps step_started by index', () => {
    expect(mapAgentEvent({ type: 'step_started', step_index: 2 })).toEqual({
      type: 'step_started',
      index: 2,
    });
  });

  it('maps step_done, normalizing status to done unless failed', () => {
    expect(mapAgentEvent({ type: 'step_done', step_index: 1, status: 'ok' })).toMatchObject({
      type: 'step_done',
      index: 1,
      status: 'done',
    });
    expect(mapAgentEvent({ type: 'step_done', step_index: 1, status: 'failed' })).toMatchObject({
      status: 'failed',
    });
  });

  it('maps result to text', () => {
    expect(mapAgentEvent({ type: 'result', text: 'final' })).toEqual({ type: 'result', text: 'final' });
  });

  it('maps error with a fallback message', () => {
    expect(mapAgentEvent({ type: 'error', message: 'boom' })).toEqual({ type: 'error', message: 'boom' });
    expect(mapAgentEvent({ type: 'error' })).toEqual({ type: 'error', message: 'error' });
  });

  it('maps done', () => {
    expect(mapAgentEvent({ type: 'done' })).toEqual({ type: 'done' });
  });

  it('drops unknown frames as null', () => {
    expect(mapAgentEvent({ type: 'heartbeat' })).toBeNull();
    expect(mapAgentEvent({})).toBeNull();
  });
});
