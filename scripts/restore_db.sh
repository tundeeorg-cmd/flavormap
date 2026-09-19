#!/usr/bin/env bash
# Restore the local flavormap database from a dump produced by scripts/dump_db.sh.
# Used to bring up a fresh clone against a frozen dataset (`make verify`).
#
# Runs psql inside the db container so the client matches the server.
#
# Usage: scripts/restore_db.sh data/exports/flavormap_20260809_120000.sql.gz
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <path-to-dump.sql.gz>" >&2
  exit 1
fi

dump_file="$1"
if [ ! -f "$dump_file" ]; then
  echo "error: $dump_file not found" >&2
  exit 1
fi

gunzip -c "$dump_file" | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
echo "Restored $dump_file -> database"
