"""scripts/export_parquet.py (T1.18): nothing personal is ever written, and nothing is
exported that the column lists do not name."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

import scripts.export_parquet as ex


def test_a_personal_data_hit_writes_nothing(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(ex, "QUERIES", {
        "clean": "SELECT 'แกงทดสอบ'::text AS name_th",
        "leaky": "SELECT 'โทร 089-876-5432'::text AS note",
    })
    with pytest.raises(SystemExit) as refused:
        ex.export(tmp_path)
    assert "leaky.parquet:note" in str(refused.value)
    assert "089" not in str(refused.value), "the refusal must not print the value"
    assert list(tmp_path.iterdir()) == [], "a refused export must leave nothing behind"


def test_a_clean_export_is_written_and_reads_back(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(ex, "QUERIES", {"t": "SELECT 1 AS n, 'ข่า'::text AS name_th"})
    assert ex.export(tmp_path) == {"t": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["t.parquet"]
    assert pd.read_parquet(tmp_path / "t.parquet").to_dict("records") == [
        {"n": 1, "name_th": "ข่า"}
    ]


def test_every_query_names_its_columns() -> None:
    """No SELECT *: a column added to a table later must not leak into the export."""
    for table, sql in ex.QUERIES.items():
        assert not re.search(r"SELECT\s+(\w+\.)?\*|,\s*(\w+\.)?\*", sql), f"{table} selects *"


def test_method_prose_and_free_text_rationale_are_not_exported() -> None:
    sql = " ".join(ex.QUERIES.values())
    for column in ("method_text", "rationale", "method_note", "conflict_note",
                   "validation_notes", "missing_ingredients", "notes"):
        assert column not in sql, column
