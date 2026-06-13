#!/bin/bash
# Template entrypoint. Materializes the Claude Max OAuth token, then serves
# FastAPI. (Codex backend uses AZURE_OPENAI_* env vars directly — no file.)
set -euo pipefail

echo "[entrypoint] booting — node $(node -v) | python $(python -V 2>&1)"

# --- Claude Code (Max) OAuth credential ------------------------------------
# The Claude Agent SDK looks for ~/.claude/.credentials.json. We write it from
# the CLAUDE_CODE_OAUTH_TOKEN secret at runtime (never baked into the image).
CRED_DIR="${HOME:-/home/runner}/.claude"
if [[ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]]; then
  mkdir -p "$CRED_DIR"
  printf '{"oauth_token":"%s"}\n' "$CLAUDE_CODE_OAUTH_TOKEN" > "$CRED_DIR/.credentials.json"
  chmod 600 "$CRED_DIR/.credentials.json"
  echo "[entrypoint] Claude OAuth token materialized"
else
  echo "[entrypoint] WARN: CLAUDE_CODE_OAUTH_TOKEN unset — Claude backend will 401 (Codex backend still works if AZURE_OPENAI_* set)"
fi

# --- Serve -----------------------------------------------------------------
exec uvicorn app.app:app --host 0.0.0.0 --port 8080
