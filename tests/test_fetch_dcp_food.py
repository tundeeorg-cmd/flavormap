"""scripts/fetch_dcp_food.py's log: URL and fetch time on every row (T1.10, TIMELINE §14).
No network: the log functions are tested on synthetic results."""

from __future__ import annotations

import csv
from pathlib import Path

from scripts.fetch_dcp_food import LOG_COLUMNS, Result, doc_url, reconstruct_log, write_log


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_the_document_url_is_built_from_the_triple() -> None:
    assert doc_url("east", 5, 1) == "https://food.culture.go.th/food68/east/5/1.pdf"


def test_the_log_records_url_and_fetch_time_and_leaves_cached_times_blank(
    tmp_path: Path,
) -> None:
    result = Result(
        fetched=[("north", 1, 1, "a" * 64, 100, "2026-10-12T10:00:00+00:00"),
                 ("north", 1, 2, "b" * 64, 200, None)],
        missing=[("south", 9, 3, 404, "2026-10-12T10:00:05+00:00")],
    )
    path = tmp_path / "log.csv"
    write_log(result, path)
    rows = _read(path)
    assert list(rows[0]) == LOG_COLUMNS
    by_menu = {(r["region"], r["menu_index"]): r for r in rows}
    assert by_menu[("north", "1")]["fetched_at"] == "2026-10-12T10:00:00+00:00"
    assert by_menu[("north", "2")]["fetched_at"] == "", "a cached file's time is never guessed"
    assert by_menu[("south", "3")]["url"] == doc_url("south", 9, 3)


def test_reconstruction_adds_urls_to_an_old_log_without_touching_it(tmp_path: Path) -> None:
    old = tmp_path / "old.csv"
    old.write_text(
        "region,province_index,menu_index,outcome,http_status,sha256,bytes\n"
        "north,1,1,fetched,200," + "c" * 64 + ",319196\n"
        "east,5,2,missing,404,,\n",
        encoding="utf-8",
    )
    before = old.read_text(encoding="utf-8")
    out = tmp_path / "interim" / "rebuilt.csv"
    assert reconstruct_log(old, out) == 2
    assert old.read_text(encoding="utf-8") == before
    rows = _read(out)
    assert [r["url"] for r in rows] == [doc_url("north", 1, 1), doc_url("east", 5, 2)]
    assert all(r["fetched_at"] == "" for r in rows)
    assert rows[0]["sha256"] == "c" * 64
