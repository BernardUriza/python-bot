#!/usr/bin/env bash
# new-consumer.sh — deterministically spawn a python-bot consumer.
#
# MECHANICS ONLY, and 100% repeatable: copy the template, init git on main, set
# the feature-flag composition, prove a green web build, commit, and (optionally)
# create the GitHub repo + push. The CREATIVE seam — CLAUDE.md, .claude/rules/,
# the persona, branding — is deliberately NOT this script's job; the
# /new-consumer skill fills that from consumer.spec.md, then re-runs the build as
# the green gate. Intent comes from the LLM, mechanics from here, proof from the
# build. That split is what makes the bootstrap stop being fragile.
set -euo pipefail

TEMPLATE="${TEMPLATE:-$HOME/Documents/python-bot}"
NAME=""; MODULES=""; DEST=""; GITHUB=0; BUILD=1; PRIVATE=1

usage() {
  echo "usage: new-consumer.sh --name <name> --modules <cms,marketplace> \\"
  echo "         [--dest DIR] [--template DIR] [--github] [--public] [--no-build]"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) NAME="${2:-}"; shift 2;;
    --modules) MODULES="${2:-}"; shift 2;;
    --dest) DEST="${2:-}"; shift 2;;
    --template) TEMPLATE="${2:-}"; shift 2;;
    --github) GITHUB=1; shift;;
    --public) PRIVATE=0; shift;;
    --no-build) BUILD=0; shift;;
    *) usage;;
  esac
done
[[ -z "$NAME" ]] && usage
DEST="${DEST:-$HOME/Documents/$NAME}"

# ── preconditions ───────────────────────────────────────────────────────────
[[ -d "$TEMPLATE/.git" ]] || { echo "ERROR: template is not a git repo: $TEMPLATE" >&2; exit 1; }
[[ -e "$DEST" ]] && { echo "ERROR: dest already exists, refusing to overwrite: $DEST" >&2; exit 1; }
git -C "$TEMPLATE" fetch -q origin 2>/dev/null || true
if [[ -n "$(git -C "$TEMPLATE" status --porcelain)" ]]; then
  echo "WARN: template working tree is dirty — copying it as-is" >&2
fi

# ── copy (node_modules INCLUDED so the build-smoke runs offline) ─────────────
echo "→ copying $TEMPLATE → $DEST"
rsync -a \
  --exclude='.git/' --exclude='.next/' --exclude='out/' \
  --exclude='__pycache__/' --exclude='*.pyc' --exclude='.env' \
  --exclude='.env*.local' --exclude='storage/' --exclude='*.tsbuildinfo' \
  "$TEMPLATE/" "$DEST/"

cd "$DEST"
git init -q
git branch -m main

# ── composition: feature flags (the only "config" a thin consumer needs) ─────
cat > api/.env <<EOF
APP_NAME=$NAME-api
APP_MODULES=$MODULES
EOF
cat > web/.env.local <<EOF
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_APP_MODULES=$MODULES
EOF
# bake the composition into the committed .env.example (the consumer's identity)
if [[ -f .env.example ]]; then
  perl -0pi -e "s/^APP_MODULES=.*/APP_MODULES=$MODULES/m" .env.example
  perl -0pi -e "s/^#?\\s*NEXT_PUBLIC_APP_MODULES=.*/NEXT_PUBLIC_APP_MODULES=$MODULES/m" .env.example
fi
grep -q '.env\*.local' .gitignore 2>/dev/null || printf '\n.env*.local\n' >> .gitignore

# ── build-smoke: the green gate (never trust a copy, verify it) ──────────────
if [[ "$BUILD" -eq 1 ]]; then
  echo "→ build-smoke (web, composed as: ${MODULES:-chat only})"
  ( cd web && { [[ -d node_modules ]] || npm ci; } && npx next build >/dev/null )
  echo "✓ web build green"
fi

# ── initial commit ───────────────────────────────────────────────────────────
git add -A
git commit -q -m "chore: bootstrap $NAME from python-bot (${MODULES:-chat only})

Thin consumer composed via feature flags (APP_MODULES=$MODULES). Mechanics by
scripts/new-consumer.sh; the creative seam (CLAUDE.md, .claude/rules/, persona,
branding) is filled next from consumer.spec.md."

# ── GitHub (optional) ─────────────────────────────────────────────────────────
if [[ "$GITHUB" -eq 1 ]]; then
  VIS="--private"; [[ "$PRIVATE" -eq 1 ]] || VIS="--public"
  echo "→ creating GitHub repo $NAME ($([[ "$PRIVATE" -eq 1 ]] && echo private || echo public))"
  gh repo create "$NAME" "$VIS" --source=. --remote=origin --push
  echo "✓ pushed: $(gh repo view --json url -q .url 2>/dev/null)"
fi

echo "✓ consumer ready at $DEST (branch main)."
echo "  Next: the /new-consumer skill fills CLAUDE.md / .claude/rules / persona / branding from the spec, then re-greens the build."
