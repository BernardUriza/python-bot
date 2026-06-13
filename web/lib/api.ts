/** API base URL — single source of truth for the FastAPI backend address.
 *
 * Note on Next.js: `NEXT_PUBLIC_*` is **build-time** inlined into the bundle,
 * not read at runtime. The Azure SWA pipeline must inject this before
 * `next build`; otherwise the production chat hits localhost. */
const DEFAULT_DEV_API_URL = "http://localhost:8080";

export const API_URL = normalizeApiUrl(
  process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_DEV_API_URL,
);

// Client abort for a /chat/stream turn. MUST stay LONGER than the backend's
// APP_CHAT_TURN_TIMEOUT_S (600s) so the SERVER wins the race and returns its
// own timeout message instead of the client aborting first. Heavy agentic
// turns run several minutes — a short client timeout kills them prematurely.
export const CHAT_STREAM_TIMEOUT_MS = 630_000;
export const API_REQUEST_TIMEOUT_MS = 30_000;
export const MAX_CHAT_MESSAGE_CHARS = 12_000;

function normalizeApiUrl(raw: string): string {
  const value = raw.trim();
  try {
    const url = new URL(value);
    return url.toString().replace(/\/$/, "");
  } catch {
    if (process.env.NODE_ENV !== "production") return DEFAULT_DEV_API_URL;
    throw new Error(`Invalid NEXT_PUBLIC_API_URL: ${value}`);
  }
}

/** Join a path onto the API base, normalizing the slash. */
export function apiUrl(path: string): string {
  const tail = path.startsWith("/") ? path : `/${path}`;
  return `${API_URL}${tail}`;
}

/** Optional shared API key — same caveat as `API_URL`: `NEXT_PUBLIC_*` is
 * **build-time** inlined, so it ends up in the bundle a user can read in
 * DevTools. That's intentional: this is NOT a secret, it's a public gate.
 * The real cost-control floor is the API-side per-IP rate limit (see
 * api/app/auth.py:limiter). Leave unset in dev — the API fail-opens. */
export const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

export function newClientRequestId(prefix = "web"): string {
  const random =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
  return `${prefix}-${random}`;
}

/** Build the headers needed to talk to the API. Centralized so a future
 * scheme change (e.g. Bearer JWT) is one edit, and so we never accidentally
 * ship a request that forgets the key. */
export function apiHeaders(extra?: HeadersInit): HeadersInit {
  const base: Record<string, string> = {
    "X-Client-Request-ID": newClientRequestId(),
  };
  if (API_KEY) base["X-API-Key"] = API_KEY;
  if (extra instanceof Headers) {
    extra.forEach((v, k) => (base[k] = v));
  } else if (Array.isArray(extra)) {
    for (const [k, v] of extra) base[k] = v;
  } else if (extra) {
    Object.assign(base, extra);
  }
  return base;
}
