# python-bot — fullstack fi template

The canonical clean template for a new fullstack agent app. Clone it, fill the
seam, and ship. It carries the **full shipped stack with NO business logic**:

- **`api/`** — FastAPI + [fi_runner](https://github.com/BernardUriza/free-intelligence)
  agent (Claude / Codex backends), longitudinal `ConversationStore` memory,
  optional RAG, anti-drift guards, and a `/chat/stream` SSE endpoint with live
  chain-of-thought.
- **`web/`** — Next.js 16 (static export) + React 19 + Tailwind v4. A streaming
  chat front that renders the agent's plan → tool calls → token stream → result.
- **`.github/workflows/`** — Azure deploy backbone: Container Apps (OIDC + GHCR)
  for the API, Static Web Apps for the front. "What's on `main` IS what's live."
- **`infra/`** — local Postgres + pgvector for RAG dev (optional).

> Memory and the agent are **fi-concentrated by doctrine**: no hand-rolled LLM
> client, no bespoke SQLite memory. Everything routes through `fi_runner` /
> `fi-core`. If you find yourself reimplementing what `fi` already ships, stop.

## The seam (what a new project fills)

Everything else is infrastructure you shouldn't need to touch. Three edits:

1. **Persona** — `api/app/personas/assistant.md` (content, not code).
2. **MCP servers** — `_MCP_SERVERS` in `api/app/runner.py` (empty by default).
   Add the npm CLI for each to `api/Dockerfile`.
3. **Branding** — `web/lib/site.ts` + the `app-*` tokens in
   `web/app/globals.css` (six colors, one edit point).

## Run it locally (tracer bullet)

```bash
# API — conda-native (fi-core/fi-runner are NOT on PyPI)
cd api
mamba env create -f environment.yml && conda activate app
export CLAUDE_CODE_OAUTH_TOKEN="$(claude setup-token)"   # or set APP_BACKEND=codex
uvicorn app.app:app --reload --port 8080
curl localhost:8080/health        # → {"ok": true, ...}

# Web — in another shell
cd web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8080 npm run dev   # → http://localhost:3000
```

## Deploy (Azure)

Both workflows trigger on push to `main` touching their half. They expect:

| Where | Name | Kind |
|---|---|---|
| API | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` | variables (OIDC) |
| API | `AZURE_CONTAINER_APP_NAME`, `AZURE_RESOURCE_GROUP` | variables |
| Web | `NEXT_PUBLIC_API_URL` | variable (inlined at build) |
| Web | `NEXT_PUBLIC_API_KEY`, `AZURE_STATIC_WEB_APPS_API_TOKEN` | secrets |
| API | `CLAUDE_CODE_OAUTH_TOKEN`, `APP_API_KEY`, `CORS_ALLOW_ORIGINS` | Container App env (set out-of-band) |

The OIDC federated credential subject is `repo:<owner>/<repo>:ref:refs/heads/main`.
The first GHCR image push lands `private` — flip the `<repo>/api` package to
`public` once so Container Apps can pull it.

See `.env.example` for the full env surface.
