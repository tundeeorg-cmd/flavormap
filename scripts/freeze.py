"""T2.10: the data freeze (Sun 13 Dec 2026). Dry run by default.

    uv run python -m scripts.freeze              (make freeze)            checks only
    uv run python -m scripts.freeze --execute    (make freeze EXECUTE=1)  on/after 13 Dec

**Dry run** (any day) checks, and changes nothing:
- the git tree is clean;
- every migration file is applied;
- the database PDPA scan is clean;
- the tag is not taken.

It prints what ``--execute`` would do.

**--execute** is refused before ``FREEZE_DATE`` unless ``--before-freeze-date`` is given
(a deliberate override, for a rehearsal on a scratch branch). In order:
1. Run the checks; stop on any failure.
2. Write the lexicon coverage snapshot (``scripts.lexicon_coverage``) and the status
   snapshot (``scripts.status --snapshot``).
3. Take a dump (``scripts/dump_db.sh``) and record its SHA-256.
4. Write ``data/coverage/freeze_YYYYMMDD.md``. Aggregates only (HD-28): rows per
   register and per source, migrations, the dump's name and checksum, the git commit.
5. Commit the snapshots and the manifest, and create the annotated tag
   ``data-freeze-v1`` locally.

**Never done here:** ``git push`` of the tag, and the off-laptop backup
(``make backup TO=…``, which needs the researcher's passphrase). Both are printed as the
researcher's next steps. T2.10's done-when ("tag pushed; dump in two places") is met only
after them.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import subprocess
from pathlib import Path

from src.config import DATA_DIR, EXPORTS_DIR, MIGRATIONS_DIR, REPO_ROOT
from src.db import get_connection
from src.ingest.pdpa import scan_database

FREEZE_DATE = datetime.date(2026, 12, 13)
TAG = "data-freeze-v1"
COVERAGE_DIR = DATA_DIR / "coverage"

COUNTS_QUERY = """
SELECT r.register, rr.source_id, count(*)
  FROM recipes r JOIN raw_recipes rr USING (raw_id)
 GROUP BY 1, 2 ORDER BY 1, 2
"""
TABLES = ("raw_recipes", "recipes", "recipe_ingredients", "province_attribution",
          "canonical_ingredients", "ingredient_aliases", "state_dish_names",
          "informants", "interview_dishes", "cook_along_log")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()


def check() -> list[tuple[str, bool, str]]:
    """(check, passed, detail) for every precondition."""
    out = []
    dirty = [ln for ln in _git("status", "--porcelain", "--untracked-files=no").splitlines()
             if ln.strip()]   # untracked files are not part of a tag
    out.append(("git tree clean", not dirty,
                f"{len(dirty)} changed path(s)" if dirty else "clean"))
    files = sorted(p.stem for p in MIGRATIONS_DIR.glob("*.sql"))
    conn = get_connection()
    try:
        applied = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
        missing = [f for f in files if f not in applied and f.split("_")[0] not in applied]
        out.append(("migrations applied", not missing,
                    f"{len(files)} files" + (f"; missing {missing}" if missing else "")))
        leaks = scan_database(conn)
        out.append(("PDPA database scan", not leaks,
                    f"{len(leaks)} finding(s)" if leaks else "clean"))
    finally:
        conn.close()
    taken = TAG in _git("tag", "--list", TAG).splitlines()
    out.append((f"tag {TAG} free", not taken, "already exists" if taken else "free"))
    return out


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(day: datetime.date, dump: Path, commit: str) -> str:
    """The freeze record: counts only, no names, no strings (HD-28)."""
    conn = get_connection()
    try:
        by_source = conn.execute(COUNTS_QUERY).fetchall()
        tables = {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]  # type: ignore[index]
                  for t in TABLES}
        migrations = conn.execute("SELECT count(*) FROM schema_migrations").fetchone()[0]  # type: ignore[index]
    finally:
        conn.close()
    lines = [f"# Data freeze {TAG} — {day.isoformat()}", "",
             "Written by `make freeze EXECUTE=1` (T2.10). Counts only (HD-28).", "",
             f"- git commit at freeze: `{commit}`",
             f"- migrations applied: {migrations}",
             f"- dump: `{dump.name}`, SHA-256 `{sha256(dump)}`", "",
             "| register | source | recipes |", "|---|---|---|"]
    lines += [f"| {reg} | {src} | {n} |" for reg, src, n in by_source]
    lines += ["", "| table | rows |", "|---|---|"]
    lines += [f"| {t} | {n} |" for t, n in tables.items()]
    lines += ["", "Researcher's steps after this: `git push origin "
              f"{TAG}` and `make backup TO=…` (T2.10 done-when: tag pushed, dump in two "
              "places)."]
    return "\n".join(lines) + "\n"


def execute(day: datetime.date) -> int:
    subprocess.run(["uv", "run", "python", "-m", "scripts.lexicon_coverage"], cwd=REPO_ROOT,
                   check=True)
    subprocess.run(["uv", "run", "python", "-m", "scripts.status", "--snapshot"],
                   cwd=REPO_ROOT, check=True)
    before = set(EXPORTS_DIR.glob("flavormap_*.sql.gz"))
    subprocess.run(["scripts/dump_db.sh"], cwd=REPO_ROOT, check=True)
    new = sorted(set(EXPORTS_DIR.glob("flavormap_*.sql.gz")) - before)
    if len(new) != 1:
        print(f"freeze: expected one new dump, found {len(new)}; stopping")
        return 1
    commit = _git("rev-parse", "--short", "HEAD")
    out = COVERAGE_DIR / f"freeze_{day:%Y%m%d}.md"
    out.write_text(manifest(day, new[0], commit), encoding="utf-8")
    # Exactly the committed kinds (.gitignore exceptions): counts-only snapshots.
    _git("add", str(out), str(COVERAGE_DIR / f"lexicon_{day:%Y%m%d}.csv"),
         str(COVERAGE_DIR / f"status_{day.isoformat()}.md"))
    _git("commit", "-m", f"data({TAG}): freeze snapshot {day.isoformat()}")
    _git("tag", "-a", TAG, "-m", f"Data freeze {day.isoformat()} (T2.10); dump {new[0].name}")
    print(f"froze: {out.name}, dump {new[0].name}, tag {TAG} (local, not pushed)")
    print(f"next (researcher): git push origin {TAG}; make backup TO=…")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--before-freeze-date", action="store_true",
                    help="allow --execute before 13 Dec (rehearsal only)")
    args = ap.parse_args(argv)
    day = datetime.date.today()
    results = check()
    for name, ok, detail in results:
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: {detail}")
    if not args.execute:
        print(f"dry run: nothing changed. On or after {FREEZE_DATE} `make freeze EXECUTE=1` "
              "writes the coverage and status snapshots, a dump, the freeze manifest, and "
              f"tags {TAG} locally.")
        return 0 if all(ok for _, ok, _ in results) else 2
    if day < FREEZE_DATE and not args.before_freeze_date:
        print(f"refused: the freeze date is {FREEZE_DATE}; today is {day}")
        return 1
    if not all(ok for _, ok, _ in results):
        print("refused: a check failed")
        return 1
    return execute(day)


if __name__ == "__main__":
    raise SystemExit(main())
