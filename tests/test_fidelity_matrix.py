"""The RQ4 pipeline-fidelity matrix: src/viz/fidelity_matrix.py and its DB script.

Ordering is tested hardest because it is a recorded decision (HD-25) and the one
thing about this figure §5 warns can silently turn a result into noise.
"""

from __future__ import annotations

import datetime
from collections.abc import Iterator
from pathlib import Path

import pytest

from scripts.make_fidelity_matrix import rows_from_db
from src.db import get_connection
from src.ingest.cook_along import FIDELITY_FIELDS
from src.viz.fidelity_matrix import CLASSES, DishRow, order_dishes, render

D = datetime.date


def _row(label: str, day: int, **cells: str | None) -> DishRow:
    return DishRow(label, D(2027, 4, day), {c: cells.get(c) for c in CLASSES})


def test_classes_follow_the_spec_and_the_schema() -> None:
    # §6's order, and one class per fidelity_* column in cook_along_log.
    assert CLASSES == ("quantities", "order", "technique", "specificity", "completeness")
    assert tuple(f"fidelity_{c}" for c in CLASSES) == FIDELITY_FIELDS


def test_most_information_lost_comes_first() -> None:
    rows = [
        _row("a", 1, quantities="survived"),
        _row("b", 2, quantities="lost", order="lost"),
        _row("c", 3, quantities="degraded"),
    ]
    assert [r.label for r in order_dishes(rows)] == ["b", "c", "a"]


def test_ties_break_by_cook_date_not_by_name() -> None:
    rows = [_row("ก", 9, order="lost"), _row("ฮ", 2, order="lost")]
    assert [r.label for r in order_dishes(rows)] == ["ฮ", "ก"]


def test_not_recorded_scores_zero_never_as_a_loss() -> None:
    blank = _row("blank", 1)
    survived = _row("survived", 2, **{c: "survived" for c in CLASSES})
    assert blank.loss == survived.loss == 0


@pytest.mark.parametrize("n", [0, 1, 8])
def test_render_writes_a_png(tmp_path: Path, n: int) -> None:
    rows = [
        DishRow(f"ข้าวซอย{i}", D(2027, 4, i + 1),
                {c: ("lost", "degraded", None)[i % 3] for c in CLASSES},
                classifier_gets_wrong=i < 2)
        for i in range(n)
    ]
    out = render(rows, tmp_path / "m.png")
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


# ── database ──────────────────────────────────────────────────────────────────

_SOURCE_ID = "_test_fidelity_src"
_KEY = "test_fidelity_1"


@pytest.fixture
def logged_cook() -> Iterator[int]:
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
        recipe_id = conn.execute(
            """INSERT INTO recipes (raw_id, name_th, register)
               VALUES (%s, 'ทดสอบ', 'commercial') RETURNING recipe_id""",
            (raw_id,),
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO cook_along_log (log_key, recipe_id, cook_date,
                   classifier_gets_wrong, fidelity_quantities, fidelity_order)
               VALUES (%s, %s, '2027-04-01', true, 'lost', 'degraded')""",
            (_KEY, recipe_id),
        )
        conn.commit()
        yield recipe_id
    finally:
        conn.rollback()
        conn.execute("DELETE FROM cook_along_log WHERE log_key = %s", (_KEY,))
        conn.execute(
            """DELETE FROM recipes WHERE raw_id IN
                   (SELECT raw_id FROM raw_recipes WHERE source_id = %s)""",
            (_SOURCE_ID,),
        )
        conn.execute("DELETE FROM raw_recipes WHERE source_id = %s", (_SOURCE_ID,))
        conn.execute("DELETE FROM sources WHERE source_id = %s", (_SOURCE_ID,))
        conn.commit()
        conn.close()


def test_rows_from_db_maps_each_column_to_its_class(logged_cook: int) -> None:
    rows = [r for r in rows_from_db() if r.cook_date == D(2027, 4, 1) and r.label == "ทดสอบ"]
    assert len(rows) == 1
    row = rows[0]
    assert row.classifier_gets_wrong is True
    assert row.cells == {
        "quantities": "lost", "order": "degraded",
        "technique": None, "specificity": None, "completeness": None,
    }
