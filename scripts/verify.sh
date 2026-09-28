#!/usr/bin/env bash
# Fresh-clone reproducibility check (CLAUDE.md §2.2), run on a THROWAWAY database.
#
# Usage: scripts/verify.sh            (or: make verify)
#
# Brings up a second, isolated copy of the database stack: its own Compose project
# (flavormap_verify), its own host port, its own volume. It applies every migration to
# that empty database, runs the full test suite against it, and tears it down. The live
# database, its container and its volume are never touched.
#
# Why this exists: `make verify` used to be `db-reset test`, and db-reset runs
# `docker compose down -v`, which deletes the LIVE volume. Running the reproducibility
# check destroyed the local corpus. The isolation used here was proven on 2026-09-28:
# with COMPOSE_PROJECT_NAME, DB_PORT and DATABASE_URL overridden, every docker compose
# command resolves to the separate project and volume (see the restore-testing commits).
#
# DATABASE_URL for the throwaway stack is derived from .env with only the port changed,
# and is never printed.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

VERIFY_PORT="${VERIFY_PORT:-5439}"
export COMPOSE_PROJECT_NAME=flavormap_verify
export DB_PORT="$VERIFY_PORT"
DATABASE_URL="$(uv run python -c "
from psycopg.conninfo import make_conninfo
from src.config import get_settings
print(make_conninfo(get_settings().database_url, port='$VERIFY_PORT'))
")"
export DATABASE_URL

# Refuse to run unless every override resolves away from the live stack.
resolved_project="$(docker compose config --format json | uv run python -c "import json,sys; print(json.load(sys.stdin)['name'])")"
if [ "$resolved_project" != "flavormap_verify" ]; then
  echo "refused: compose resolved to project '$resolved_project', not flavormap_verify" >&2
  exit 1
fi
if docker compose -p flavormap ps --format '{{.Ports}}' 2>/dev/null | grep -q ":${VERIFY_PORT}->"; then
  echo "refused: port $VERIFY_PORT is the live database's port; set VERIFY_PORT" >&2
  exit 1
fi

cleanup() { docker compose down -v >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "verify: starting throwaway stack (project flavormap_verify, port $VERIFY_PORT)"
docker compose down -v >/dev/null 2>&1 || true
docker compose up -d --wait >/dev/null
uv run python -m scripts.migrate
uv run pytest
uv run ruff check .
uv run mypy
echo "verify: passed on a fresh, migrated, empty database. Live database untouched."
