#!/usr/bin/env bash
# Restore a dump produced by scripts/dump_db.sh.
#
# Usage: scripts/restore_db.sh [--force] [--db NAME] <path-to-dump.sql.gz>
#
#   --db NAME   restore into database NAME instead of $POSTGRES_DB (e.g. a throwaway
#               database for checking a dump without touching the live one)
#   --force     replace a target database that already contains tables
#
# How it works, and why (tested 2026-09-28, see git log):
#
# 1. Refuses a target that already holds tables unless --force is given. Restoring on
#    top of existing tables is how data gets lost silently: after `make db-reset` (which
#    re-runs the migrations) the old script reported success over 84 errors and dropped
#    all 201 province_attribution rows.
# 2. Restores into a fresh STAGING database created from template0, which is truly
#    empty. A database created normally in this image already has PostGIS's tiger and
#    topology schemas, which collide with the dump's own.
# 3. Runs psql with ON_ERROR_STOP and --single-transaction, so the first error aborts
#    the restore and exits non-zero. Nothing can report success over a failure.
# 4. Only then drops the target and renames staging into its place. A failed restore,
#    even with --force, leaves the existing target exactly as it was.
#
# Runs psql inside the db container so the client matches the server. Never prints a
# connection string.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

usage() { echo "Usage: $0 [--force] [--db NAME] <path-to-dump.sql.gz>" >&2; exit 1; }

force=0
target=""
dump_file=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --force) force=1; shift ;;
    # An explicit but empty --db is an error, never a fall-through to the live default.
    --db) [ "$#" -ge 2 ] && [ -n "$2" ] || usage; target="$2"; shift 2 ;;
    -*) usage ;;
    *) [ -z "$dump_file" ] || usage; dump_file="$1"; shift ;;
  esac
done
[ -n "$dump_file" ] || usage

if [ ! -f "$dump_file" ]; then
  echo "error: $dump_file not found" >&2
  exit 1
fi

# Inside the container: run psql against the maintenance database, with the target name
# passed as an environment variable rather than interpolated into a shell string.
in_db() {
  docker compose exec -T -e PGOPTIONS='-c client_min_messages=warning' \
    -e TARGET_DB="${target}" -e STAGING_DB="${staging:-}" db sh -c "$1"
}

if [ -z "$target" ]; then
  target="$(docker compose exec -T db sh -c 'printf %s "$POSTGRES_DB"')"
fi
if ! printf '%s' "$target" | grep -Eq '^[a-z_][a-z0-9_]{0,50}$'; then
  echo "error: database name '$target' must be lowercase letters, digits and underscores" >&2
  exit 1
fi
staging="${target}_restore_staging"

q() { in_db "psql -U \"\$POSTGRES_USER\" -d postgres -v ON_ERROR_STOP=1 -Atc \"$1\""; }

exists="$(q "select count(*) from pg_database where datname = '${target}'")"
if [ "$exists" = "1" ]; then
  n_tables="$(in_db 'psql -U "$POSTGRES_USER" -d "$TARGET_DB" -Atc "select count(*) from pg_tables where schemaname = '"'"'public'"'"'"')"
  if [ "$n_tables" != "0" ] && [ "$force" -ne 1 ]; then
    echo "refused: database '$target' already has $n_tables tables. Restoring on top of" >&2
    echo "existing tables loses data silently. Re-run with --force to replace it" >&2
    echo "(the current contents are only dropped after the restore succeeds)." >&2
    exit 1
  fi
fi

echo "Restoring $dump_file into staging database '$staging'..."
in_db 'dropdb -U "$POSTGRES_USER" --if-exists "$STAGING_DB" && createdb -U "$POSTGRES_USER" -T template0 "$STAGING_DB"'

if ! gunzip -c "$dump_file" \
    | in_db 'psql -q -U "$POSTGRES_USER" -d "$STAGING_DB" -v ON_ERROR_STOP=1 --single-transaction' \
    > /dev/null; then
  in_db 'dropdb -U "$POSTGRES_USER" --if-exists "$STAGING_DB"' || true
  echo "FAILED: the restore hit an error and was rolled back. '$target' was not changed." >&2
  exit 1
fi

in_db 'dropdb -U "$POSTGRES_USER" --if-exists --force "$TARGET_DB" \
  && psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 -qc "ALTER DATABASE \"$STAGING_DB\" RENAME TO \"$TARGET_DB\""'

summary="$(in_db 'psql -U "$POSTGRES_USER" -d "$TARGET_DB" -Atc "select (select count(*) from recipes) || '"'"' recipes, '"'"' || (select count(*) from province_attribution) || '"'"' province attributions, '"'"' || (select count(*) from schema_migrations) || '"'"' migrations'"'"'"')"
echo "Restored $dump_file -> '$target': $summary"
