import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { loadOrCreateSessionId, rotateSessionId } from './session';

const KEY = 'fi-template.session-id';

describe('session id persistence', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => localStorage.clear());

  it('mints and persists an id on first load', () => {
    expect(localStorage.getItem(KEY)).toBeNull();
    const id = loadOrCreateSessionId();
    expect(id).toBeTruthy();
    expect(localStorage.getItem(KEY)).toBe(id);
  });

  it('returns the SAME id across reloads (survives a fresh call)', () => {
    const first = loadOrCreateSessionId();
    const second = loadOrCreateSessionId();
    expect(second).toBe(first);
  });

  it('rotate mints a different id and persists it', () => {
    const original = loadOrCreateSessionId();
    const rotated = rotateSessionId();
    expect(rotated).not.toBe(original);
    expect(localStorage.getItem(KEY)).toBe(rotated);
    // a subsequent load now returns the rotated id, not the original
    expect(loadOrCreateSessionId()).toBe(rotated);
  });
});
