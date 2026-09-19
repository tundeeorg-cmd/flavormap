#!/usr/bin/env bash
# Dump the local flavormap database to data/exports/ as a timestamped, gzip-compressed
# archive. Used for the Phase 2 dataset freeze and for `make verify` reproducibility
# checks (CLAUDE.md §Tests, §Phase 2 exit).
#
# Runs pg_dump inside the db container, so the client always matches the server
# (Postgres 15) and nothing needs installing on the host. The connection string is
# never printed, because it contains the password.
#
# Usage: scripts/dump_db.sh
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

mkdir -p data/exports
timestamp="$(date +%Y%m%d_%H%M%S)"
out="data/exports/flavormap_${timestamp}.sql.gz"
trap 'rm -f "$out"' ERR

docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | gzip > "$out"
echo "Dumped database -> $out ($(du -h "$out" | cut -f1))"
