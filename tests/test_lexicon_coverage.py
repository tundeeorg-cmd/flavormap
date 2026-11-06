"""scripts/lexicon_coverage.py (T1.17), on synthetic rows. Strings and canonical ids are
invented placeholders; nothing here is a lexicon decision."""

from __future__ import annotations

import csv
import datetime
from pathlib import Path

from scripts.lexicon_coverage import COLUMNS, Coverage, coverage, write_snapshot
from scripts.lexicon_worklist import mapping_index

ROWS = [
    ("dcp_food", "official", 1, "แกงทดสอบ"),
    ("dcp_food", "official", 1, "แกงทดสอบ"),          # same string twice: one mention
    ("dcp_food", "official", 2, "  แกงทดสอบ "),        # whitespace differs: same key
    ("dcp_food", "official", 2, "ข้าวทดสอบ"),
    ("kapook_cooking", "commercial", 3, "แกงทดสอบ 2 ช้อน"),  # a whole line: not mapped
    ("kapook_cooking", "commercial", 3, "ผักทดสอบ"),
]
INDEX = mapping_index([
    ("แกงทดสอบ", "can_test_1", "herb"),
    ("ผักทดสอบ", "can_test_2", "vegetable"),
    ("ผักทดสอบ", "can_test_3", "vegetable"),           # mapped twice: conflict
])


def _by_scope() -> dict[str, Coverage]:
    return {c.scope: c for c in coverage(ROWS, INDEX)}


def test_a_mention_is_one_string_per_recipe() -> None:
    total = _by_scope()["all"]
    assert total.mentions == 5


def test_mapped_unmapped_and_conflicting_are_counted_separately() -> None:
    total = _by_scope()["all"]
    assert (total.mapped, total.conflicting) == (2, 1)
    assert total.share == 2 / 5


def test_registers_and_sources_are_reported_separately() -> None:
    scopes = _by_scope()
    official = scopes["register:official"]
    commercial = scopes["source:kapook_cooking"]
    assert (official.mapped, official.mentions) == (2, 3)
    assert (commercial.mapped, commercial.mentions) == (0, 2)


def test_the_committed_snapshot_holds_counts_only(tmp_path: Path) -> None:
    """It is committed (T1.17), so no ingredient string may appear in it (HD-3, HD-28)."""
    path = write_snapshot(coverage(ROWS, INDEX), datetime.date(2026, 10, 12), tmp_path)
    assert path.name == "lexicon_20261012.csv"
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert tuple(rows[0]) == COLUMNS
    text = path.read_text(encoding="utf-8")
    assert not any("฀" <= ch <= "๿" for ch in text), "Thai text in the snapshot"
    for row in rows[1:]:
        assert row[1] in {"all", "rq1_registers"} or row[1].split(":")[0] in {"register", "source"}
        assert all(cell.replace(".", "").isdigit() for cell in row[2:])


def test_excluded_mentions_are_left_out_of_the_share() -> None:
    """Strings the researcher excluded (water, equipment) are neither mapped nor gaps."""
    from scripts.lexicon_worklist import EXCLUDED

    index = dict(INDEX)
    index.update(mapping_index([("ข้าวทดสอบ", EXCLUDED, EXCLUDED)]))
    total = {c.scope: c for c in coverage(ROWS, index)}["all"]
    assert (total.mentions, total.mapped, total.excluded) == (5, 2, 1)
    assert total.share == 2 / 4
    assert total.strings_mapped == 1  # แกงทดสอบ; the excluded string is not "mapped"



def test_reviewed_mapping_is_counted_beside_all_entries() -> None:
    """A mention is reviewed-mapped when its string maps to a trusted entry."""
    total = {c.scope: c for c in coverage(ROWS, INDEX, reviewed={"แกงทดสอบ"})}["all"]
    assert (total.mapped, total.mapped_reviewed) == (2, 2)
    total = {c.scope: c for c in coverage(ROWS, INDEX, reviewed=set())}["all"]
    assert total.mapped_reviewed == 0 and total.reviewed_share == 0.0
    assert {c.scope: c for c in coverage(ROWS, INDEX)}["all"].mapped_reviewed == 0


def test_rq1_registers_scope_leaves_state_promotional_out() -> None:
    """HD-6 coverage scope (2026-11-06): the paper's coverage is over RQ1's registers;
    state-promotional mentions are reported in their own row only."""
    rows = [*ROWS, ("tat_food", "state_promotional", 9, "แกงทดสอบ"),
            ("tat_food", "state_promotional", 9, "อื่นทดสอบ")]
    scopes = {c.scope: c for c in coverage(rows, INDEX)}
    rq1, base = scopes["rq1_registers"], _by_scope()["all"]
    assert (rq1.mentions, rq1.mapped) == (base.mentions, base.mapped)
    assert scopes["all"].mentions == base.mentions + 2
    assert scopes["register:state_promotional"].mentions == 2
