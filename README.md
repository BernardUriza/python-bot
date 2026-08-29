# python-bot — fullstack fi template

The canonical clean template for a new fullstack agent app. Clone it, fill the
seam, and ship. It carries the **full shipped stack with NO business logic**:

- **`api/`** — FastAPI + [fi_runner](https://github.com/BernardUriza/free-intelligence)
  agent over **AIRE** (the only backend fi-runner ships since 2026-08-29 — the
  agent runs server-side, so there is no CLI and no Anthropic credential in this
  image), longitudinal `ConversationStore` memory, optional RAG, anti-drift
  guards, and a `/chat/stream` SSE endpoint with live chain-of-thought.
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
2. **Tools** — `BASE_TOOLS` in `api/app/backend.py`: the NAMES of tools from
   AIRE's registry your agent may call (`task_tracker` by default, `rag_store`
   per turn when a `corpus_id` is passed). A tool AIRE's registry does not ship
   is rejected at the door with a 422. Local MCP servers do **not** work on this
   route — only a spec's name crosses, so `_MCP_SERVERS` in `runner.py` runs
   nothing.
3. **Branding** — `web/lib/site.ts` + the `app-*` tokens in
   `web/app/globals.css` (six colors, one edit point).

## Run it locally (tracer bullet)

```bash
# API — conda-native (fi-core/fi-runner are NOT on PyPI)
cd api
mamba env create -f environment.yml && conda activate app
export AIRE_GATE_URL="https://your-aire-door/"   # both required, or every
export AIRE_AUTH_TOKEN="…"                       # turn fails at the door
uvicorn app.app:app --reload --port 8080
curl localhost:8080/health        # → {"ok": true, ...}

`/health` answers even with the door unconfigured — it probes this process, not
AIRE. Send a real turn through `/chat/stream` before believing the stack is up.

# Web — in another shell
cd web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8080 npm run dev   # → http://localhost:3000
```

The chat surface persists its session id in `localStorage`, so a page reload
keeps talking to the same `ConversationStore` thread (the longitudinal memory);
the built-in **New Chat** button rotates to a fresh session.

## Test & CI

`.github/workflows/ci.yml` gates every PR and push to `main` — main must stay
green because "what's on `main` IS what's live."

```bash
cd web && npm test        # vitest — wire mapper + session persistence
cd api && pytest          # boundary glue: validation, auth gate, wire, SSE, /health
```

The API tests stub the agent runtime (`fi_runner`/`fi-core` are conda + git
only) in `api/conftest.py`, so the api CI job is a plain `pip install` — no
monorepo clone. They cover the template infrastructure, not fi internals.

## Deploy (Azure)

Both workflows trigger on push to `main` touching their half. They expect:

| Where | Name | Kind |
|---|---|---|
| API | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` | variables (OIDC) |
| API | `AZURE_CONTAINER_APP_NAME`, `AZURE_RESOURCE_GROUP` | variables |
| Web | `NEXT_PUBLIC_API_URL` | variable (inlined at build) |
| Web | `NEXT_PUBLIC_API_KEY`, `AZURE_STATIC_WEB_APPS_API_TOKEN` | secrets |
| API | `AIRE_GATE_URL`, `AIRE_AUTH_TOKEN`, `APP_API_KEY`, `CORS_ALLOW_ORIGINS` | Container App env (set out-of-band) |

The OIDC federated credential subject is `repo:<owner>/<repo>:ref:refs/heads/main`.
The first GHCR image push lands `private` — flip the `<repo>/api` package to
`public` once so Container Apps can pull it.

See `.env.example` for the full env surface.
