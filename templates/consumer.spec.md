# Consumer spec — <app-name>

> Minimal functional requirements. The `/new-consumer` skill turns THIS into a
> configured python-bot consumer: it runs `scripts/new-consumer.sh` for the
> mechanics, then fills the creative seam below from these answers, and verifies
> a green build. Fill what you know; leave the rest as `TBD` (the skill asks).

## Identity
- **name**: <kebab-case — becomes the dir, the GitHub repo, and APP_NAME>
- **org / for whom**: <the collective, person, or business>
- **one-liner**: <what the app does, one sentence>

## Composition — feature flags (→ APP_MODULES)
The chat assistant is always on. Add the optional capabilities this app needs:
- [ ] **cms** — content manager (self-publish crónicas/notes; `/cms`)
- [ ] **marketplace** — storefront + payment seam (`/marketplace`)
- modules line: `<e.g. cms,marketplace>`

## Persona — `api/app/personas/assistant.md`
- **voice**: <tone; who it speaks as>
- **knows / grounds on**: <the domain facts, sources, history it should know>
- **refuses / out of scope**: <safety + scope lines>

## Branding — `web/lib/site.ts` + `web/app/globals.css` tokens
- **site name / title / description**:
- **6 color tokens** (bg, surface, border, brand, accent, muted): <hex each, or "derive from <vibe/refs>">

## Content & sections (app-specific)
- **seed content**: <crónicas / products to preload, or "none yet">
- **key sections**: <e.g. tienda, crónicas, participa, galería>

## Governance — `CLAUDE.md` + `.claude/rules/`
- **hard prohibitions for this app**: <written as bans; e.g. "no auto-post", domain/safety constraints>
- **audience running it**: <technical level — shapes copy & UX>

## Deploy
- **github**: <yes/no · private|public>
- **domain**: <if known, else TBD — day-N>
