#!/usr/bin/env bash
# Dump the local flavormap database to data/exports/ as a timestamped, gzip-compressed
# archive. Used for the Phase 2 dataset freeze and for `make verify` reproducibility
# checks (CLAUDE.md §Tests, §Phase 2 exit).
#
# Usage: scripts/dump_db.sh
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${DATABASE_URL:?DATABASE_URL not set — check .env}"

mkdir -p data/exports
timestamp="$(date +%Y%m%d_%H%M%S)"
out="data/exports/flavormap_${timestamp}.sql.gz"

pg_dump "$DATABASE_URL" | gzip > "$out"
echo "Dumped $DATABASE_URL -> $out"
