"""HD-6 Q5 splits (src/clean/lexicon.py), the grouped worksheet (scripts/lexicon_groups.py)
and applying the researcher's filled worksheet (scripts/lexicon_apply.py). All strings and
ids are synthetic; nothing here is a lexicon decision."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.lexicon_apply import append, decisions, plan
from scripts.lexicon_groups import group_worklist, groups_to_reach, multi_parts, suggestion_key
from scripts.lexicon_worklist import build_worklist
from src.clean.lexicon import (
    ALIAS_COLUMNS,
    ALIASES_FILE,
    CANONICAL_COLUMNS,
    CANONICAL_FILE,
    CONFLATION_COLUMNS,
    CONFLATIONS_FILE,
    SPLIT_COLUMNS,
    SPLITS_FILE,
    LexiconError,
    read_lexicon,
)

ENTRIES = [
    "ING_0001,ปลาร้า,fermented fish,protein_fish,true,,",
    "ING_0002,ปลาเค็ม,salted fish,protein_fish,false,,",
    "ING_0003,เกลือ,salt,other,false,,",
] + [f"ING_{i:04d},ผักทดสอบ{i},test veg {i},vegetable,false,," for i in range(4, 40)]


def _write(tmp: Path, aliases: list[str] = (), splits: list[str] | None = None) -> Path:
    files = {CANONICAL_FILE: (CANONICAL_COLUMNS, ENTRIES),
             ALIASES_FILE: (ALIAS_COLUMNS, list(aliases)),
             CONFLATIONS_FILE: (CONFLATION_COLUMNS, [])}
    if splits is not None:
        files[SPLITS_FILE] = (SPLIT_COLUMNS, splits)
    for name, (cols, lines) in files.items():
        (tmp / name).write_text("\n".join([",".join(cols), *lines]) + "\n", encoding="utf-8")
    return tmp


# --- splits -------------------------------------------------------------------------

def test_a_split_maps_one_string_to_every_entry_it_names(tmp_path: Path) -> None:
    lex = read_lexicon(_write(tmp_path, splits=["ปลาร้าหรือปลาเค็ม,ING_0001",
                                                "ปลาร้าหรือปลาเค็ม,ING_0002"]))
    assert lex.entries_for(" ปลาร้าหรือปลาเค็ม ") == ("ING_0001", "ING_0002")
    assert lex.entries_for("ปลาร้า") == ("ING_0001",)
    assert lex.entries_for("ไม่มี") == ()


def test_the_splits_file_is_optional(tmp_path: Path) -> None:
    assert read_lexicon(_write(tmp_path)).splits == {}


@pytest.mark.parametrize("splits, message", [
    (["ปลาร้าหรือปลาเค็ม,ING_0001"], "needs two or more"),
    (["ปลาร้า,ING_0001", "ปลาร้า,ING_0002"], "already mapped"),
    (["x,ING_0001", "x,ING_9999"], "not an entry"),
    (["x,ING_0001", "x,ING_0001", "x,ING_0002"], "twice"),
])
def test_bad_splits_are_refused(tmp_path: Path, splits: list[str], message: str) -> None:
    with pytest.raises(LexiconError, match=message):
        read_lexicon(_write(tmp_path, splits=splits))


# --- grouped worksheet --------------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("พริกขี้หนู 10 เม็ด", "พริกขี้หนู"),
    ("ใบมะกรูดหั่นฝอย", "ใบมะกรูด"),           # preparation word dropped (Q2)
    ("กุ้งแห้ง 1 ช้อนโต๊ะ", "กุ้ง"),             # state word dropped (Q2)
    ("เกลือป่น (สำหรับหมัก)", "เกลือ"),
    ("สับปะรด", "สับปะรด"),                     # สับ inside a name is kept
    ("พริกขี้หนูสวน", "พริกขี้หนูสวน"),          # cultivar (Q1) is not grouped by key
    ("เต้าหู้ไข่ 2 หลอด", "เต้าหู้ไข่"),
    ("พริกชี้ฟ้าแดง หั่นเฉียง", "พริกชี้ฟ้าแดง"),
])
def test_suggestion_key(raw: str, expected: str) -> None:
    assert suggestion_key(raw) == expected


def test_multi_parts_flags_lists_and_alternatives_only() -> None:
    assert multi_parts("ปลาร้าหรือปลาเค็ม") == ["ปลาร้า", "ปลาเค็ม"]
    assert multi_parts("ข่า ตะไคร้ หอมแดง") == ["ข่า", "ตะไคร้", "หอมแดง"]
    assert multi_parts("กะทิ+เครื่องแกง") == ["กะทิ", "เครื่องแกง"]
    assert multi_parts("ใบมะกรูด") == []
    assert multi_parts("ภาพจาก : เพจทดสอบ") == []


def test_groups_are_ordered_by_total_mentions() -> None:
    rows = [("s", "commercial", 1, "เกลือ 1 ช้อนชา"), ("s", "commercial", 2, "เกลือป่น"),
            ("s", "commercial", 3, "เกลือ"), ("s", "official", 4, "ปลาร้า"),
            ("s", "official", 5, "ปลาร้า")]
    groups = group_worklist(build_worklist(rows, {}, with_similar=False))
    assert [g.key for g in groups] == ["เกลือ", "ปลาร้า"]
    assert groups[0].mentions == 3 and len(groups[0].members) == 3
    assert groups_to_reach(groups, 0.6) == 1


# --- applying the worksheet ---------------------------------------------------------

def _sheet(rows: list[tuple[str, str, str, str]]) -> list[dict[str, str]]:
    return [{"group_rank": g, "name_th": s, "group_decision": gd, "decision": d}
            for g, s, gd, d in rows]


def test_decisions_reads_group_defaults_overrides_and_skips() -> None:
    sheet = _sheet([("1", "เกลือ", "ING_0003", ""), ("1", "เกลือป่น", "", ""),
                    ("1", "เกลือทะเล", "", "skip"), ("1", "เกลือทดสอบ", "", "ING_0004"),
                    ("2", "ปลาร้า", "", "")])
    assert [(s, d) for _, s, d in decisions(sheet)] == [
        ("เกลือ", "ING_0003"), ("เกลือป่น", "ING_0003"), ("เกลือทดสอบ", "ING_0004")]


def test_plan_splits_maps_and_refuses(tmp_path: Path) -> None:
    d = _write(tmp_path)
    ok = plan(_sheet([("1", "เกลือป่น", "", "ING_0003"),
                      ("2", "ปลาร้าหรือปลาเค็ม", "", "ING_0001|ING_0002"),
                      ("3", "ปลาร้า", "", "ING_0001")]), d)
    assert ok.aliases == [("เกลือป่น", "ING_0003")]
    assert ok.splits == [("ปลาร้าหรือปลาเค็ม", ("ING_0001", "ING_0002"))]
    assert ok.already == 1 and ok.errors == []
    bad = plan(_sheet([("1", "x", "", "ING_9999"), ("2", "y", "", "salt"),
                       ("3", "ปลาร้า", "", "ING_0002")]), d)
    assert len(bad.errors) == 3


def test_append_writes_files_that_validate(tmp_path: Path) -> None:
    d = _write(tmp_path)
    planned = plan(_sheet([("1", "เกลือป่น", "", "ING_0003"),
                           ("2", "ปลาร้าหรือปลาเค็ม", "", "ING_0001|ING_0002")]), d)
    append(d, planned)
    lex = read_lexicon(d)
    assert lex.entries_for("เกลือป่น") == ("ING_0003",)
    assert lex.entries_for("ปลาร้าหรือปลาเค็ม") == ("ING_0001", "ING_0002")
    with (d / ALIASES_FILE).open(encoding="utf-8") as f:
        assert list(csv.reader(f))[-1] == ["เกลือป่น", "ING_0003"]
