#!/usr/bin/env bash
# Restore the local flavormap database from a dump produced by scripts/dump_db.sh.
# Used to bring up a fresh clone against a frozen dataset (`make verify`).
#
# Usage: scripts/restore_db.sh data/exports/flavormap_20260809_120000.sql.gz
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${DATABASE_URL:?DATABASE_URL not set — check .env}"

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <path-to-dump.sql.gz>" >&2
  exit 1
fi

dump_file="$1"
if [ ! -f "$dump_file" ]; then
  echo "error: $dump_file not found" >&2
  exit 1
fi

gunzip -c "$dump_file" | psql "$DATABASE_URL"
echo "Restored $dump_file -> $DATABASE_URL"
