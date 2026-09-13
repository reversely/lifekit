#!/usr/bin/env bash
# Bring up a LifeKit instance on a box (docs/content/deployments-and-approval.md 1.1).
# Run from the repo root on the box. Idempotent: every step skips what is already done.
#
#   bash scripts/box_up.sh            # environment, library, web build, serve on :8008
#   bash scripts/box_up.sh --no-serve # everything except starting the server
#
# Settings (defaults suit the GN100 with the Nano NIM on port 30081):
#   LIFEKIT_MODEL_SMALL   openai:http://localhost:30081/v1:nvidia/nemotron-nano-9b-v2
#   LIFEKIT_MODEL_ANSWER  same as small unless set
#   LIFEKIT_LOOP          on
#   LIFEKIT_PORT          8008
set -euo pipefail
cd "$(dirname "$0")/.."

export LIFEKIT_MODEL_SMALL="${LIFEKIT_MODEL_SMALL:-openai:http://localhost:30081/v1:nvidia/nemotron-nano-9b-v2}"
export LIFEKIT_LOOP="${LIFEKIT_LOOP:-on}"
PORT="${LIFEKIT_PORT:-8008}"

step() { printf '\n== %s\n' "$*"; }

step "python environment"
command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; }
uv sync --all-groups

step "model endpoint"
base="${LIFEKIT_MODEL_SMALL#openai:}"; base="${base%:*}"
if curl -sf -m 5 "$base/models" >/dev/null; then
  echo "reachable: $base"
else
  echo "not reachable: $base (the API still serves; answers and the loop will fail until it is)"
fi

step "library"
if [ ! -s packs/library.sqlite ]; then
  for shelf in packs/shelves/*/; do uv run python -m lifekit.library.fetch "$(basename "$shelf")" || true; done
  uv run python -m lifekit.library.build
else
  echo "packs/library.sqlite present ($(du -h packs/library.sqlite | cut -f1))"
fi

step "web build"
if [ ! -f web/dist/index.html ]; then
  command -v npm >/dev/null || { echo "npm missing: install Node 20+ and rerun"; exit 1; }
  (cd web && npm ci && cp ../packs/library.sqlite public/library.sqlite && npm run build)
else
  echo "web/dist present"
fi
cp -f packs/library.sqlite web/dist/library.sqlite

if [ "${1:-}" = "--no-serve" ]; then exit 0; fi
step "serve on :$PORT"
exec uv run uvicorn lifekit.api:app --host 0.0.0.0 --port "$PORT"
