"""A read-only, plain-text snapshot of where the project stands (``make status``).

Collects counts from the database and a few facts from disk, then renders them as text.
Three rules shape everything here:

1. **Never modify the database.** The connection is opened with
   ``default_transaction_read_only=on``, so even a mistaken write would be rejected by
   Postgres, not merely avoided by this code.
2. **Never raise on a missing piece.** A fresh clone may have no database, an empty
   one, or one migrated only part way. Every query runs on its own in autocommit mode,
   and any failure — missing table, missing column, no server — becomes ``n/a`` for
   that line. Exception text is never printed: a connection error can name the host
   and user, and there is no reason to put any of that in a committed file.
3. **Only aggregates and public facts.** Counts, dates, file names, and province names
   (public geography). No row content from any table, so no personal data can reach
   the output. ``render(public=True)`` also drops the per-province name lists, which
   are DCP-derived coverage (HD-3); that is the form committed by
   ``make status-snapshot`` (HD-28).

RQ readiness follows CLAUDE.md §4 (Bible v4). A question whose input depends on
fieldwork reports that part as ``blocked-on-fieldwork`` while no interview data exists,
not as a failure.
"""

from __future__ import annotations

import datetime
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg

from src.clean.lexicon import OTHER_CEILING, check_categories
from src.config import DOCS_DIR, EXPORTS_DIR, MIGRATIONS_DIR, REPO_ROOT

TOTAL_PROVINCES = 77
REGISTERS = ("official", "commercial", "domestic")
BACKUP_MAX_AGE_DAYS = 7
RQ4_PLANNED_DISHES = 8  # CLAUDE.md §7.4

NA = "n/a"

_DATE_FIELD = re.compile(r"\*\*Date[^*\n]*:\*\*\s*(\d{4}-\d{2}-\d{2})")
_EXPORT_STAMP = re.compile(r"(\d{8})_(\d{6})")


# ── database access ──────────────────────────────────────────────────────────

class ReadOnlyDB:
    """Read-only, autocommit, failure-tolerant access. Every method returns None
    instead of raising, so a missing table degrades one line, not the report."""

    def __init__(self, dsn: str | None) -> None:
        self.conn: psycopg.Connection[Any] | None = None
        if dsn is None:
            return
        try:
            self.conn = psycopg.connect(
                dsn,
                autocommit=True,
                connect_timeout=3,
                options="-c default_transaction_read_only=on",
            )
        except Exception:
            self.conn = None

    @property
    def reachable(self) -> bool:
        return self.conn is not None

    def rows(self, sql: str, params: tuple[object, ...] = ()) -> list[tuple[Any, ...]] | None:
        if self.conn is None:
            return None
        try:
            return self.conn.execute(sql, params).fetchall()
        except Exception:
            return None

    def scalar(self, sql: str, params: tuple[object, ...] = ()) -> int | None:
        rows = self.rows(sql, params)
        if not rows or rows[0][0] is None:
            return None
        return int(rows[0][0])

    def count(self, table: str) -> int | None:
        return self.scalar(f"SELECT count(*) FROM {table}")

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()


def _default_dsn() -> str | None:
    try:
        from src.config import get_settings

        return get_settings().database_url
    except Exception:
        return None


# ── collection ───────────────────────────────────────────────────────────────

@dataclass
class Status:
    today: datetime.date
    db_reachable: bool = False
    counts: dict[str, int | None] = field(default_factory=dict)
    by_register: dict[str, int] | None = None
    by_confidence: dict[str, int] | None = None
    provinces_covered: dict[str, int | None] = field(default_factory=dict)
    provinces_missing: dict[str, list[str] | None] = field(default_factory=dict)
    provinces_total: int = TOTAL_PROVINCES
    lexicon: dict[str, int | None] = field(default_factory=dict)
    categories: dict[str, int] | None = None
    migrations_applied: int | None = None
    migrations_present: int = 0
    container_up: bool | None = None
    newest_backup: str | None = None
    backup_age_days: int | None = None
    decisions_dated: int = 0
    decisions_latest: str | None = None
    rq_inputs: dict[str, int | None] = field(default_factory=dict)


def _grouped(db: ReadOnlyDB, sql: str) -> dict[str, int] | None:
    rows = db.rows(sql)
    return None if rows is None else {str(k): int(v) for k, v in rows}


def _collect_db(db: ReadOnlyDB, s: Status) -> None:
    s.db_reachable = db.reachable
    for table in ("raw_recipes", "recipes", "recipe_ingredients", "canonical_ingredients",
                  "ingredient_aliases", "province_attribution", "informants",
                  "interview_dishes", "cook_along_log"):
        s.counts[table] = db.count(table)
    s.by_register = _grouped(db, "SELECT register, count(*) FROM recipes GROUP BY 1")
    s.by_confidence = _grouped(
        db, "SELECT confidence, count(*) FROM province_attribution GROUP BY 1")

    n_provinces = db.count("provinces")
    if n_provinces:
        s.provinces_total = n_provinces
    for register in REGISTERS:
        s.provinces_covered[register] = db.scalar(
            """SELECT count(DISTINCT pa.province_code)
                 FROM recipes r JOIN province_attribution pa USING (recipe_id)
                WHERE r.register = %s AND pa.province_code IS NOT NULL""",
            (register,),
        )
        missing = db.rows(
            """SELECT p.name_en FROM provinces p
                WHERE NOT EXISTS (
                    SELECT 1 FROM recipes r JOIN province_attribution pa USING (recipe_id)
                     WHERE r.register = %s AND pa.province_code = p.province_code)
                ORDER BY p.name_en""",
            (register,),
        )
        # With no provinces loaded, "every province is missing" is not knowable.
        s.provinces_missing[register] = (
            [str(r[0]) for r in missing] if missing is not None and n_provinces else None
        )

    s.lexicon = {
        "entries": s.counts["canonical_ingredients"],
        "with_gloss": db.scalar(
            "SELECT count(*) FROM canonical_ingredients WHERE btrim(name_en) <> ''"),
        "uncategorised": db.scalar(
            "SELECT count(*) FROM canonical_ingredients "
            "WHERE category IS NULL OR btrim(category) = ''"),
        "other": db.scalar(
            "SELECT count(*) FROM canonical_ingredients WHERE category = 'other'"),
        "fermented": db.scalar(
            "SELECT count(*) FROM canonical_ingredients WHERE is_fermented"),
    }
    s.categories = _grouped(
        db, "SELECT category, count(*) FROM canonical_ingredients "
            "WHERE category IS NOT NULL GROUP BY 1")
    s.migrations_applied = db.count("schema_migrations")

    def with_ingredients(register: str) -> int | None:
        return db.scalar(
            """SELECT count(DISTINCT r.recipe_id) FROM recipes r
                 JOIN recipe_ingredients ri USING (recipe_id) WHERE r.register = %s""",
            (register,),
        )

    s.rq_inputs = {
        "official_with_ingredients": with_ingredients("official"),
        "commercial_with_ingredients": with_ingredients("commercial"),
        "official_recipes": (s.by_register or {}).get("official", 0)
        if s.by_register is not None else None,
        "clean_view": db.count("v_recipes_clean"),
        "interview_dishes": s.counts["interview_dishes"],
        "stated_absences": db.scalar(
            "SELECT count(*) FROM interview_dishes WHERE btrim(stated_absence) <> ''"),
        "cook_alongs": s.counts["cook_along_log"],
        "official_with_endangerment": db.scalar(
            "SELECT count(*) FROM recipes WHERE register = 'official' "
            "AND endangerment IS NOT NULL"),
    }


def _container_up() -> bool | None:
    try:
        out = subprocess.run(
            ["docker", "compose", "ps", "--status", "running", "--services"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=5, check=False,
        )
    except Exception:
        return None
    if out.returncode != 0:
        return None
    return "db" in out.stdout.split()


def _newest_backup(exports: Path, today: datetime.date) -> tuple[str | None, int | None]:
    files = [p for p in exports.glob("*") if p.is_file() and not p.name.startswith(".")]
    if not files:
        return None, None

    def stamp(p: Path) -> datetime.date:
        m = _EXPORT_STAMP.search(p.name)
        if m:
            return datetime.datetime.strptime(m.group(1), "%Y%m%d").date()
        return datetime.date.fromtimestamp(p.stat().st_mtime)

    newest = max(files, key=lambda p: (stamp(p), p.name))
    return newest.name, (today - stamp(newest)).days


def _decisions(path: Path) -> tuple[int, str | None]:
    """Sections (## headings) carrying at least one **Date…:** YYYY-MM-DD field, and the
    latest such date anywhere in the file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return 0, None
    sections = text.split("\n## ")[1:]
    dated = [s for s in sections if _DATE_FIELD.search(s)]
    dates = _DATE_FIELD.findall(text)
    return len(dated), max(dates) if dates else None


def collect(
    dsn: str | None | Callable[[], str | None] = _default_dsn,
    today: datetime.date | None = None,
    exports_dir: Path = EXPORTS_DIR,
    decisions_path: Path = DOCS_DIR / "decisions.md",
    migrations_dir: Path = MIGRATIONS_DIR,
    check_container: bool = True,
) -> Status:
    s = Status(today=today or datetime.date.today())
    db = ReadOnlyDB(dsn() if callable(dsn) else dsn)
    try:
        _collect_db(db, s)
    finally:
        db.close()
    s.migrations_present = len(list(migrations_dir.glob("*.sql")))
    s.container_up = _container_up() if check_container else None
    s.newest_backup, s.backup_age_days = _newest_backup(exports_dir, s.today)
    s.decisions_dated, s.decisions_latest = _decisions(decisions_path)
    return s


# ── readiness ────────────────────────────────────────────────────────────────

def _state(values: list[int | None]) -> str:
    if any(v is None for v in values):
        return NA
    present = [v for v in values if v]
    if not present:
        return "no"
    return "yes" if len(present) == len(values) else "partial"


def _n(v: int | None) -> str:
    return NA if v is None else str(v)


def _fieldwork(v: int | None, what: str) -> str:
    if v is None:
        return f"{what} {NA}"
    return f"blocked-on-fieldwork (0 {what})" if v == 0 else f"{v} {what}"


def rq_readiness(i: dict[str, int | None]) -> list[str]:
    """One line per research question: state, then the counts it depends on."""
    off, com = i.get("official_with_ingredients"), i.get("commercial_with_ingredients")
    dishes = i.get("interview_dishes")
    lines = [
        f"RQ1 {_state([off, com])} — recipes with cleaned ingredients: official {_n(off)}, "
        f"commercial {_n(com)}; domestic side {_fieldwork(dishes, 'interview dishes')}",
        f"RQ2 {_state([i.get('clean_view')])} — {_n(i.get('clean_view'))} recipes in "
        f"v_recipes_clean; validation {_fieldwork(i.get('stated_absences'), 'stated absences')}",
    ]

    def fieldwork_state(v: int | None, other: int | None) -> str:
        if v is None or other is None:
            return NA
        if v == 0:
            return "blocked-on-fieldwork"
        return "yes" if other else "partial"

    official = i.get("official_recipes")
    lines.append(
        f"RQ3 {fieldwork_state(dishes, official)} — {_n(official)} official recipes, "
        f"{_n(dishes)} interview dishes"
    )
    cooks = i.get("cook_alongs")
    if cooks is None:
        rq4 = NA
    else:
        rq4 = "no" if cooks == 0 else ("yes" if cooks >= RQ4_PLANNED_DISHES else "partial")
    lines.append(f"RQ4 {rq4} — {_n(cooks)} of {RQ4_PLANNED_DISHES} cook-alongs logged")
    endangered = i.get("official_with_endangerment")
    lines.append(
        f"RQ5 {fieldwork_state(dishes, endangered)} — {_n(endangered)} official recipes "
        f"with an endangerment level, {_n(dishes)} interview dishes"
    )
    return lines


# ── rendering ────────────────────────────────────────────────────────────────

def _breakdown(d: dict[str, int] | None, keys: tuple[str, ...]) -> str:
    if d is None:
        return NA
    return ", ".join(f"{k} {d.get(k, 0)}" for k in keys)


def _category_lines(categories: dict[str, int] | None) -> list[str]:
    """HD-27's check, via the same function the authoring worklist uses."""
    if categories is None:
        return [f"  by category (HD-27)    {NA}"]
    check = check_categories(categories)
    if check.total == 0:
        return ["  by category (HD-27)    none yet"]
    lines = ["  by category (HD-27)    " + ", ".join(
        f"{c} {n}" for c, n in check.by_category.items() if n)]
    if check.unknown:
        lines.append(f"  ⚠ not in HD-27's list  {', '.join(check.unknown)}")
    return lines


def render(s: Status, public: bool = False) -> str:
    """The snapshot as plain text. `public=True` omits per-province name lists (HD-28)."""
    out: list[str] = [f"FlavorMap status — {s.today.isoformat()}", ""]
    c = s.counts

    out.append("Corpus")
    if not s.db_reachable:
        out.append("  database: not reachable (every database line below is n/a)")
    out += [
        f"  raw_recipes            {_n(c.get('raw_recipes'))}",
        f"  recipes                {_n(c.get('recipes'))}"
        f"  ({_breakdown(s.by_register, REGISTERS)})",
        f"  recipe_ingredients     {_n(c.get('recipe_ingredients'))}",
        f"  canonical_ingredients  {_n(c.get('canonical_ingredients'))}",
        f"  ingredient_aliases     {_n(c.get('ingredient_aliases'))}",
        f"  province_attribution   {_n(c.get('province_attribution'))}"
        f"  ({_breakdown(s.by_confidence, ('high', 'medium', 'low'))})",
        f"  informants             {_n(c.get('informants'))}",
        f"  interview_dishes       {_n(c.get('interview_dishes'))}",
        f"  cook_along_log         {_n(c.get('cook_along_log'))}",
        "",
        f"Coverage — provinces with at least one recipe, of {s.provinces_total}",
    ]
    for register in REGISTERS:
        covered = s.provinces_covered.get(register)
        out.append(f"  {register:<11}{_n(covered)}")
        missing = s.provinces_missing.get(register)
        if public or covered is None or missing is None:
            continue
        if covered == 0:
            out.append("             none yet")
        elif missing:
            out.append(f"             zero: {', '.join(missing)}")

    lx = s.lexicon
    entries, other = lx.get("entries"), lx.get("other")
    if entries is None or other is None:
        other_line = NA
    elif entries == 0:
        other_line = "0 (no entries yet)"
    else:
        share = other / entries
        flag = f"  ⚠ over the {OTHER_CEILING:.0%} ceiling (HD-27)" if share > OTHER_CEILING else ""
        other_line = f"{other} ({share:.1%}){flag}"
    out += [
        "",
        "Lexicon",
        f"  canonical entries      {_n(entries)}",
        f"  with English gloss     {_n(lx.get('with_gloss'))}",
        f"  uncategorised          {_n(lx.get('uncategorised'))}",
        *_category_lines(s.categories),
        f"  category 'other'       {other_line}",
        f"  fermented              {_n(lx.get('fermented'))}",
        "",
        "Pipeline health",
        f"  migrations             {_n(s.migrations_applied)} applied of "
        f"{s.migrations_present} files"
        + ("  ⚠ unapplied migrations" if s.migrations_applied is not None
           and s.migrations_applied < s.migrations_present else ""),
        "  db container           "
        + {True: "up", False: "not running", None: NA}[s.container_up],
    ]
    if s.newest_backup is None:
        out.append("  newest backup          none in data/exports/  ⚠ no backup")
    else:
        stale = (s.backup_age_days or 0) > BACKUP_MAX_AGE_DAYS
        out.append(
            f"  newest backup          {s.newest_backup}, {s.backup_age_days} days old"
            + (f"  ⚠ older than {BACKUP_MAX_AGE_DAYS} days — run make db-dump" if stale else "")
        )
    out += [
        "",
        "Decisions",
        f"  dated entries          {s.decisions_dated}",
        f"  most recent            {s.decisions_latest or NA}",
        "",
        "Research questions — is the input data there yet?",
        *(f"  {line}" for line in rq_readiness(s.rq_inputs)),
        "",
    ]
    return "\n".join(out)
