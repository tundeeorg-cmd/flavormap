#!/usr/bin/env bash
# Encrypted off-laptop backup of the interview files and the newest database dump (HD-31).
#
# Usage: scripts/backup.sh <destination-directory>      (or: make backup TO=<dir>)
#
# What it does:
#   1. Refuses a destination on the same disk as the repo. A backup on the laptop it is
#      meant to protect is not a backup.
#   2. Bundles data/interviews/*.toml (gitignored, HD-30), the newest
#      data/exports/flavormap_*.sql.gz, and a MANIFEST of SHA-256 checksums.
#   3. Encrypts the bundle with gpg, symmetric AES-256. gpg asks for the passphrase
#      itself; it never passes through this script, a file, or an agent session.
#   4. Verifies before reporting success: decrypts the new file and checks every
#      checksum against the originals.
#
# Restore:  gpg --decrypt <file>.tar.gz.gpg | tar -xz
#           then scripts/restore_db.sh --force flavormap_backup/exports/<dump>.sql.gz
#           and copy flavormap_backup/interviews/*.toml back into data/interviews/.
#
# Lose the passphrase and the backup is unrecoverable. Write it down somewhere safe.
#
# Test-only hooks, used by tests/test_backup.py with a throwaway GNUPGHOME and a dummy
# passphrase. Never set them for a real backup:
#   FLAVORMAP_BACKUP_TEST_ALLOW_SAME_DISK=1    skip the same-disk refusal
#   FLAVORMAP_BACKUP_TEST_PASSPHRASE_FILE=...  non-interactive gpg
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
repo="$(pwd)"

dest="${1:-}"
if [ -z "$dest" ]; then
  echo "Usage: $0 <destination-directory>   (e.g. make backup TO=/Volumes/MyDrive)" >&2
  exit 1
fi
if [ ! -d "$dest" ] || [ ! -w "$dest" ]; then
  echo "error: '$dest' is not a writable directory. Is the drive plugged in?" >&2
  exit 1
fi

same_disk="$(uv run python -c 'import os, sys; print(int(os.stat(sys.argv[1]).st_dev == os.stat(sys.argv[2]).st_dev))' "$dest" "$repo")"
if [ "$same_disk" = "1" ] && [ "${FLAVORMAP_BACKUP_TEST_ALLOW_SAME_DISK:-}" != "1" ]; then
  echo "refused: '$dest' is on the same disk as this repo. Back up to an external drive" >&2
  echo "or a cloud-synced folder, so the copy survives losing this laptop (HD-31)." >&2
  exit 1
fi

dump="$(ls -t data/exports/flavormap_*.sql.gz 2>/dev/null | head -1 || true)"
if [ -z "$dump" ]; then
  echo "error: no database dump in data/exports/. Run make db-dump first." >&2
  exit 1
fi
shopt -s nullglob
interviews=(data/interviews/*.toml)
shopt -u nullglob

# A dump older than the newest interview file may predate loading it.
for f in "${interviews[@]}"; do
  if [ "$f" -nt "$dump" ]; then
    echo "warning: $f is newer than $dump. If it has been loaded since, run" >&2
    echo "make db-dump first so the database copy includes it." >&2
    break
  fi
done

gpg_args=(--quiet)
if [ -n "${FLAVORMAP_BACKUP_TEST_PASSPHRASE_FILE:-}" ]; then
  gpg_args+=(--batch --yes --pinentry-mode loopback
             --passphrase-file "$FLAVORMAP_BACKUP_TEST_PASSPHRASE_FILE")
fi

stage="$(mktemp -d)"
check="$(mktemp -d)"
trap 'rm -rf "$stage" "$check"' EXIT
bundle="$stage/flavormap_backup"
mkdir -p "$bundle/interviews" "$bundle/exports"
[ "${#interviews[@]}" -eq 0 ] || cp "${interviews[@]}" "$bundle/interviews/"
cp "$dump" "$bundle/exports/"

uv run python - "$bundle" "$(git rev-parse --short HEAD 2>/dev/null || echo unknown)" <<'PY'
import datetime, hashlib, sys
from pathlib import Path
bundle, commit = Path(sys.argv[1]), sys.argv[2]
lines = [f"# FlavorMap backup, {datetime.datetime.now().isoformat(timespec='seconds')}, "
         f"repo commit {commit}", "# sha256  path"]
for p in sorted(bundle.rglob("*")):
    if p.is_file():
        lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(bundle)}")
(bundle / "MANIFEST").write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

out="$dest/flavormap_backup_$(date +%Y%m%d_%H%M%S).tar.gz.gpg"
echo "Encrypting ${#interviews[@]} interview file(s) and $(basename "$dump")."
echo "gpg will ask for the passphrase. Lose it and this backup cannot be opened."
tar -C "$stage" -czf - flavormap_backup \
  | gpg "${gpg_args[@]}" --symmetric --cipher-algo AES256 --output "$out"

# Verify: decrypt what was written and compare every checksum with the originals.
if ! gpg "${gpg_args[@]}" --decrypt "$out" | tar -xz -C "$check"; then
  rm -f "$out"
  echo "FAILED: the new backup did not decrypt; it has been removed." >&2
  exit 1
fi
if ! uv run python - "$bundle" "$check/flavormap_backup" <<'PY'
import sys
from pathlib import Path
a, b = Path(sys.argv[1]), Path(sys.argv[2])
files = lambda root: {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
sys.exit(0 if files(a) == files(b) else 1)
PY
then
  rm -f "$out"
  echo "FAILED: the decrypted backup does not match the originals; it has been removed." >&2
  exit 1
fi

echo "Backed up -> $out ($(du -h "$out" | cut -f1)). Verified: decrypts and matches."
