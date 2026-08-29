#!/bin/bash
# Template entrypoint. Serves FastAPI — nothing else to do at boot.
#
# It used to materialize a Claude Max OAuth token into ~/.claude/.credentials.json
# for the local Agent SDK. Since the 2026-08-29 AIREBackend consolidation the
# agent runs on AIRE's server, which holds its own Anthropic credential: this
# container carries only the door's bearer token (AIRE_AUTH_TOKEN), and it stays
# an env var — never a file.
set -euo pipefail

echo "[entrypoint] booting — python $(python -V 2>&1)"

if [[ -z "${AIRE_GATE_URL:-}" || -z "${AIRE_AUTH_TOKEN:-}" ]]; then
  echo "[entrypoint] WARN: AIRE_GATE_URL / AIRE_AUTH_TOKEN unset — /health will"
  echo "[entrypoint]       still answer, but every chat turn will fail with"
  echo "[entrypoint]       'AIRE door not configured'."
fi

# --- Serve -------------------------------------------------------------------
exec uvicorn app.app:app --host 0.0.0.0 --port 8080
