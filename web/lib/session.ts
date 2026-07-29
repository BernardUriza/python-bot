/** Client session id — the key the API's ConversationStore replays memory under.
 *
 * The api/ requires a non-empty `session_id` and replays every prior turn filed
 * under it (longitudinal memory). If the web minted a fresh random id on each
 * page load, that memory would be invisible to the user — a reload would start a
 * blank conversation even though the backend still holds the history. So we
 * PERSIST the id in localStorage: reload keeps the thread, and "new chat"
 * deliberately rotates it.
 *
 * Pure + guarded so it runs under SSR/static-export (no `window`) and in tests.
 */

const STORAGE_KEY = 'fi-template.session-id';

function randomId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID();
  return `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

/** Best-effort localStorage — absent under SSR, may throw in private mode. */
function storage(): Storage | null {
  try {
    return typeof window !== 'undefined' ? window.localStorage : null;
  } catch {
    return null;
  }
}

/** Return the persisted session id, minting + storing one on first call.
 * Falls back to an ephemeral id when storage is unavailable (SSR / locked down). */
export function loadOrCreateSessionId(): string {
  const store = storage();
  if (!store) return randomId();
  try {
    const existing = store.getItem(STORAGE_KEY);
    if (existing) return existing;
    const fresh = randomId();
    store.setItem(STORAGE_KEY, fresh);
    return fresh;
  } catch {
    return randomId();
  }
}

/** Rotate to a fresh session id (a "new conversation"), persisting it. Returns
 * the new id so callers can update their ref without a re-read. */
export function rotateSessionId(): string {
  const fresh = randomId();
  const store = storage();
  try {
    store?.setItem(STORAGE_KEY, fresh);
  } catch {
    /* ephemeral fallback — the returned id is still used for this surface */
  }
  return fresh;
}
