"""Cook-along loader (RQ4): src/ingest/cook_along.py and scripts/load_cook_along.py.

Three levels, mirroring tests/test_pdpa.py:

1. **Parse** — validation of one file's keys and values. No database.
2. **Files on disk** — every tracked cook-along file (and the template) is clean.
3. **Database** — upsert on log_key, all-or-nothing loads, and no personal data lands.

Personal-data fixtures are invented and use the surname ทดสอบ ("test"), as in
tests/test_pdpa.py.
"""

from __future__ import annotations

import datetime
from collections.abc import Iterator
from pathlib import Path

import pytest

from scripts.load_cook_along import load, read_all
from src.config import COOK_ALONG_DIR
from src.db import get_connection
from src.ingest.cook_along import (
    ALLOWED_KEYS,
    CookAlongError,
    log_files,
    parse_entry,
    read_entry,
)
from src.ingest.pdpa import find_leaks

MINIMAL: dict[str, object] = {"recipe_id": 1, "cook_date": datetime.date(2026, 10, 4)}


# ── 1. parse ──────────────────────────────────────────────────────────────────

def test_minimal_entry_leaves_everything_else_null() -> None:
    e = parse_entry("2026-10-04_test", MINIMAL)
    assert e.log_key == "2026-10-04_test"
    assert e.recipe_id == 1
    assert e.fidelity_order is None
    assert e.result_recognizable is None
    assert e.classifier_gets_wrong is False


def test_full_entry_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "2026-10-04_khao_soi.toml"
    path.write_text(
        """
recipe_id = 7
cook_date = 2026-10-04
result_recognizable = true
classifier_gets_wrong = true
fidelity_quantities = "lost"
fidelity_order = "degraded"
fidelity_technique = "lost"
fidelity_specificity = "survived"
fidelity_completeness = "degraded"
missing_ingredients = \"\"\"
พริกแกง — the list kept only พริก
\"\"\"
notes = "ยาย said the curry paste was wrong"
""",
        encoding="utf-8",
    )
    e = read_entry(path)
    assert e.log_key == "2026-10-04_khao_soi"
    assert e.fidelity_quantities == "lost"
    assert e.classifier_gets_wrong is True
    assert e.missing_ingredients is not None and "พริกแกง" in e.missing_ingredients


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"recipe_id": None}, "recipe_id is required"),
        ({"recipe_id": "7"}, "recipe_id is required"),
        ({"recipe_id": True}, "recipe_id is required"),
        ({"cook_date": None}, "cook_date is required"),
        ({"cook_date": "2026-10-04"}, "cook_date is required"),
        ({"cook_date": datetime.datetime(2026, 10, 4, 12)}, "cook_date is required"),
        ({"fidelity_order": "partial"}, "must be one of"),
        ({"fidelity_order": ""}, "must be one of"),
        ({"result_recognizable": "yes"}, "must be true or false"),
        ({"notes": 3}, "must be a string"),
        ({"fidelity_quantites": "lost"}, "unknown key"),
    ],
)
def test_invalid_entries_are_refused(override: dict[str, object], message: str) -> None:
    data = {**MINIMAL, **override}
    data = {k: v for k, v in data.items() if v is not None}
    with pytest.raises(CookAlongError, match=message):
        parse_entry("bad", data)


@pytest.mark.parametrize(
    "text",
    [
        "cooked with นางสมหญิง ทดสอบ",
        "call 08 1234 5678 to confirm",
        "somchai@example.com sent the recipe",
        "at เลขที่ ๙๙/๙ หมู่ ๖",
        "the shop on ถนน ทดสอบ",
    ],
)
def test_personal_data_in_any_text_field_is_refused(text: str) -> None:
    for field in ("missing_ingredients", "substitutions_made", "normalization_losses", "notes"):
        with pytest.raises(CookAlongError, match="personal data") as exc:
            parse_entry("pii", {**MINIMAL, field: text})
        # The refusal names the field, never echoes the personal data it refused.
        assert field in str(exc.value)
        assert not find_leaks(str(exc.value))


def test_people_referred_to_by_role_are_accepted() -> None:
    e = parse_entry("roles", {**MINIMAL, "notes": "ยายกับแม่ช่วยกันทำ นายอำเภอก็ชิม"})
    assert e.notes is not None


def test_blank_text_is_null_not_empty_string() -> None:
    assert parse_entry("blank", {**MINIMAL, "notes": "  \n"}).notes is None


def test_template_and_underscore_files_are_skipped(tmp_path: Path) -> None:
    (tmp_path / "_template.toml").write_text("recipe_id = 0\n", encoding="utf-8")
    (tmp_path / "2026-10-04_a.toml").write_text("", encoding="utf-8")
    assert [p.name for p in log_files(tmp_path)] == ["2026-10-04_a.toml"]


def test_read_all_reports_every_bad_file_at_once(tmp_path: Path) -> None:
    (tmp_path / "a.toml").write_text(
        'recipe_id = 1\ncook_date = 2026-10-04\nfidelity_order = "x"\n'
    )
    (tmp_path / "b.toml").write_text("not = [valid toml\n")
    (tmp_path / "c.toml").write_text("recipe_id = 1\ncook_date = 2026-10-04\n")
    with pytest.raises(CookAlongError) as exc:
        read_all(tmp_path)
    assert "a:" in str(exc.value) and "b:" in str(exc.value)
    assert "c:" not in str(exc.value)


# ── 2. files on disk ──────────────────────────────────────────────────────────

def test_template_documents_every_column() -> None:
    text = (COOK_ALONG_DIR / "_template.toml").read_text(encoding="utf-8")
    missing = [k for k in sorted(ALLOWED_KEYS) if k not in text]
    assert not missing, f"template does not mention {missing}"


def test_every_cook_along_file_on_disk_is_valid_and_clean() -> None:
    """These files are committed. A leak here is a leak into git history, which the
    loader's refusal cannot undo — so they are checked directly, not only on load."""
    for path in sorted(COOK_ALONG_DIR.glob("*.toml")):
        assert not find_leaks(path.read_text(encoding="utf-8")), path.name
    read_all(COOK_ALONG_DIR)  # raises on any invalid, non-template file


# ── 3. database ───────────────────────────────────────────────────────────────

_SOURCE_ID = "_test_cook_along_src"
_KEY = "test_cook_along_1"  # no leading "_": log_files() would skip it as a template


@pytest.fixture
def recipe_id() -> Iterator[int]:
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO sources (source_id, source_type, base_url, robots_ok, audited_on)
               VALUES (%s, 'web_scraped', 'https://example.com', true, '2026-09-28')""",
            (_SOURCE_ID,),
        )
        raw_id = conn.execute(
            """INSERT INTO raw_recipes (source_id, source_url, raw_path, content_hash)
               VALUES (%s, 'https://example.com/1', '/tmp/_test', 'deadbeef')
               RETURNING raw_id""",
            (_SOURCE_ID,),
        ).fetchone()[0]
        rid = conn.execute(
            """INSERT INTO recipes (raw_id, name_th, register, extraction_method)
               VALUES (%s, 'ทดสอบ', 'commercial', 'parsed') RETURNING recipe_id""",
            (raw_id,),
        ).fetchone()[0]
        conn.commit()
        yield rid
    finally:
        conn.rollback()
        conn.execute("DELETE FROM cook_along_log WHERE log_key LIKE 'test\\_cook\\_along\\_%'")
        conn.execute(
            """DELETE FROM recipes WHERE raw_id IN
                   (SELECT raw_id FROM raw_recipes WHERE source_id = %s)""",
            (_SOURCE_ID,),
        )
        conn.execute("DELETE FROM raw_recipes WHERE source_id = %s", (_SOURCE_ID,))
        conn.execute("DELETE FROM sources WHERE source_id = %s", (_SOURCE_ID,))
        conn.commit()
        conn.close()


def _rows(key: str) -> list[tuple[object, ...]]:
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT recipe_id, fidelity_order, notes FROM cook_along_log WHERE log_key = %s",
            (key,),
        ).fetchall()
    finally:
        conn.close()


def test_reloading_an_edited_file_updates_in_place(recipe_id: int) -> None:
    load([parse_entry(_KEY, {**MINIMAL, "recipe_id": recipe_id, "fidelity_order": "lost"})])
    load([parse_entry(_KEY, {**MINIMAL, "recipe_id": recipe_id, "fidelity_order": "degraded"})])
    assert _rows(_KEY) == [(recipe_id, "degraded", None)]


def test_an_unknown_recipe_loads_nothing(recipe_id: int) -> None:
    good = parse_entry(_KEY, {**MINIMAL, "recipe_id": recipe_id})
    bad = parse_entry("test_cook_along_2", {**MINIMAL, "recipe_id": -1})
    with pytest.raises(CookAlongError, match="not in recipes"):
        load([good, bad])
    assert _rows(_KEY) == []  # the good row was rolled back with the bad one


def test_a_file_with_personal_data_never_reaches_the_table(
    recipe_id: int, tmp_path: Path
) -> None:
    (tmp_path / f"{_KEY}.toml").write_text(
        f'recipe_id = {recipe_id}\ncook_date = 2026-10-04\nnotes = "นางสมหญิง ทดสอบ 08 1234 5678"\n',
        encoding="utf-8",
    )
    with pytest.raises(CookAlongError):
        load(read_all(tmp_path))
    assert _rows(_KEY) == []
