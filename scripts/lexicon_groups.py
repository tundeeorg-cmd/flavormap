"""Grouped authoring worksheet for the lexicon (HD-6), sorted by mention frequency.

    uv run python -m scripts.lexicon_groups [--out data/interim/lexicon_groups.csv]
    (or: make lexicon-groups)

**What changed, and why (researcher, 2026-11-06).** `scripts/lexicon_worklist.py` ranks
strings one by one and never groups them (boundary set 2026-09-29). For the DH2027
deadline the researcher asked for spelling and form variants to be **grouped as
suggestions only, every mapping decided by the researcher**. This script is that
worksheet. It still writes nothing to the lexicon and nothing to the database: the
grouping is a display order, and a mapping exists only once the researcher types an
entry id into the worksheet and runs `scripts/lexicon_apply.py`.

**How a suggested group is formed** (``suggestion_key``). Display only; it is written to
put likely variants next to each other, not to be right:

1. `src.clean.lexicon.strip_quantity` (amounts, units after a number, amount words,
   bullets) — the HD-6 Q6 prototype, used here for grouping only; the lexicon itself
   still maps raw strings (Q6 = (a)).
2. Parenthesised text and purpose phrases (``สำหรับ…``, ``ไว้…``) removed.
3. Trailing preparation and state words removed, repeatedly (``ใบมะกรูดหั่นฝอย`` →
   ``ใบมะกรูด``; ``กุ้งแห้ง`` → ``กุ้ง``), following HD-6 Q2 ("always dropped"). Only
   at the end of the string or as a separate word, so ``สับปะรด`` keeps its ``สับ``.

Strings with the same key form one group. Cultivars (Q1), processed forms (Q3) and
plant parts (Q4) are **not** grouped by the key — ``พริกขี้หนูสวน`` and ``พริกขี้หนู``
stay apart — because those boundaries are word-level judgments; the ``similar`` column
of the plain worklist still shows them side by side.

**Several ingredients in one string** (HD-6 Q5, "split all"). A string whose key still
contains ``หรือ``, ``+``, ``,``, ``และ`` or several space-separated words is flagged
``multi`` and its suggested parts are listed. It needs a split decision (two or more
entry ids).

**Columns.** One row per raw string, grouped; groups ordered by total mentions:
``group_rank``, ``suggested_group`` (the key), ``group_mentions``, ``group_cum_share``
(running share of all (recipe, string) pairs after this group), ``group_strings``,
``name_th`` (the raw string, exactly the alias you would map), ``n_recipes``, per-source
counts, ``mapped`` (``yes`` / ``split`` / ``conflict`` / blank), ``current_entry``,
``multi_parts``, then the two columns **you** fill:

- ``group_decision`` (first row of a group only): one entry id applies to every string
  in the group whose ``decision`` is blank.
- ``decision``: per string. ``ING_0001`` maps it; ``ING_0001|ING_0002`` splits it (Q5);
  ``skip`` leaves it unmapped even when ``group_decision`` is filled.

The output is DCP-derived (HD-3), so it goes to ``data/interim/`` (gitignored).
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from scripts.lexicon_worklist import (
    CONFLICT,
    MAPPED_QUERY,
    QUERY,
    SPLIT,
    WorklistRow,
    build_worklist,
    mapping_index,
)
from src.clean.lexicon import _UNITS, key, strip_quantity
from src.config import INTERIM_DIR
from src.db import get_connection

OUT = INTERIM_DIR / "lexicon_groups.csv"

# HD-6 Q2 ("always dropped"): state words; and preparation words, dropped under any
# option (stated in the question). Longest first so ซอยละเอียด goes before ซอย.
_DROP_WORDS = tuple(sorted({
    "สด", "แห้ง", "ป่น",
    "สับ", "สับละเอียด", "สับหยาบ", "ซอย", "ซอยบาง", "ซอยละเอียด", "ซอยบางๆ", "ซอยหยาบ",
    "หั่น", "หั่นฝอย", "หั่นท่อน", "หั่นชิ้น", "หั่นแว่น", "หั่นเต๋า", "หั่นบาง", "หั่นบางๆ",
    "หั่นสี่เหลี่ยม", "หั่นครึ่ง", "หั่นเป็นชิ้น", "หั่นชิ้นพอดีคำ", "ชิ้นพอดีคำ",
    "ฉีก", "ฉีกฝอย", "บุบ", "ทุบ", "ตำ", "โขลก", "บด", "บดละเอียด", "ฝาน", "ฝานบาง",
    "ขูด", "ขูดฝอย", "ปอกเปลือก", "แกะเปลือก", "ล้างสะอาด", "เด็ดใบ", "เด็ดเป็นใบ",
    "แช่น้ำ", "แช่น้ำให้นิ่ม", "ละเอียด", "หยาบ", "บางๆ", "เล็กน้อย",
}, key=len, reverse=True))
_TRAILING_DROP = re.compile(r"(?:\s*(?:" + "|".join(map(re.escape, _DROP_WORDS)) + r"))+$")
_SPACED_DROP = re.compile(r"(?<=\s)(?:" + "|".join(map(re.escape, _DROP_WORDS)) + r")(?=\s|$)")
_PARENS = re.compile(r"\([^)]*\)|\[[^\]]*\]|（[^）]*）")
_PURPOSE = re.compile(r"\s*(?:สำหรับ|ไว้|เอาไว้)\S*.*$")
_PART_SPLIT = re.compile(r"\s*(?:หรือ|\+|,|、|และ)\s*|\s+")
_MIN_LEN = 2
# A lone trailing word after a space that is a unit, a size or a filler, not a second
# ingredient ("เต้าหู้ไข่ หลอด", "พริกแดง ค่ะ", "น้ำมะนาว ปริมาณ"). Removed before
# grouping; the raw string is untouched in the worksheet.
_FILLER = frozenset(_UNITS) | frozenset({
    "ปริมาณ", "จำนวน", "ค่ะ", "คะ", "ครับ", "นะคะ", "จ้า", "ใหญ่", "เล็ก", "กลาง", "ซีก",
    "แว่น", "แง่ง", "หวี", "กล่อง", "จาน", "กิ่ง", "ก้าน", "หลอด", "อุณหภูมิห้อง",
    "แช่เย็น", "แช่เย็นจัด", "ขนาดกลาง", "ขนาดใหญ่", "ขนาดเล็ก", "พอประมาณ", "ตามชอบ",
    "ซอง", "ถ้วย", "ช้อน", "ลูก", "ผล", "หัว", "ต้น",
})
# A space-separated word that starts with a preparation verb is an instruction, not an
# ingredient ("หั่นเฉียง", "แช่น้ำจนนุ่ม", "ปอกเปลือกผ่าหลัง"). HD-6 Q2: dropped.
_PREP_WORD = re.compile(r"(?:หั่น|ซอย|สับ|แช่|ปอก|แกะ|ล้าง|ผ่า|ตัด|ฝาน|บุบ|ทุบ|ฉีก|เด็ด|"
                        r"โขลก|บด|ขูด|คั้น|ละลาย|ร่อน|เอา|กิน|ใช้)")
_CONNECTOR = re.compile(r"หรือ|\+|,|、|และ")


def suggestion_key(raw: str) -> str:
    """The display key a raw string is grouped under (module docstring). Never a
    mapping."""
    text = strip_quantity(key(raw))
    text = _PARENS.sub(" ", text)
    text = _PURPOSE.sub("", text)
    text = _SPACED_DROP.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip(" -–:*•")
    words = text.split(" ")
    while len(words) > 1 and (words[-1] in _FILLER or _TRAILING_DROP.fullmatch(words[-1])
                              or _PREP_WORD.match(words[-1])):
        words.pop()
    text = " ".join(words)
    stripped = _TRAILING_DROP.sub("", text).strip()
    if len(stripped) >= _MIN_LEN:
        text = stripped
    return text or key(raw)


def multi_parts(group_key: str) -> list[str]:
    """Suggested parts when the key still names several things (HD-6 Q5), else []."""
    parts = [p for p in _PART_SPLIT.split(group_key)
             if p and p not in ("ก็ได้",) and p not in _FILLER]
    # Explicit connectors always count; bare spaces only when every part is a word of
    # its own (≥ 3 characters), so "ข่า ตะไคร้ หอมแดง" is flagged and "ภาพจาก : …" is not.
    spaced = (" " in group_key and ":" not in group_key
              and all(len(p) >= 3 and not p.isascii() for p in parts))
    is_multi = bool(_CONNECTOR.search(group_key)) or spaced
    if not is_multi or len(parts) < 2:
        return []
    out = []
    for p in parts:
        s = _TRAILING_DROP.sub("", p).strip() or p
        if len(s) >= _MIN_LEN and s not in out:
            out.append(s)
    return out if len(out) > 1 else []


@dataclass
class Group:
    key: str
    members: list[WorklistRow] = field(default_factory=list)

    @property
    def mentions(self) -> int:
        return sum(m.n_recipes for m in self.members)


def group_worklist(worklist: list[WorklistRow]) -> list[Group]:
    """Groups ordered by total mentions, then key; members by mentions, then rank."""
    groups: dict[str, Group] = {}
    for row in worklist:
        k = suggestion_key(row.name_th)
        groups.setdefault(k, Group(k)).members.append(row)
    for g in groups.values():
        g.members.sort(key=lambda r: (-r.n_recipes, r.rank))
    return sorted(groups.values(), key=lambda g: (-g.mentions, g.key))


def groups_to_reach(groups: list[Group], share: float) -> int:
    total = sum(g.mentions for g in groups)
    covered = 0
    for i, g in enumerate(groups, start=1):
        covered += g.mentions
        if covered >= share * total:
            return i
    return len(groups)


def write_csv(groups: list[Group], out: Path) -> None:
    sources = sorted({s for g in groups for m in g.members for s in m.by_source})
    total = sum(g.mentions for g in groups) or 1
    out.parent.mkdir(parents=True, exist_ok=True)
    covered = 0
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["group_rank", "suggested_group", "group_mentions", "group_cum_share",
                    "group_strings", "name_th", "n_recipes",
                    *(f"n_{s}" for s in sources), "mapped", "current_entry",
                    "multi_parts", "group_decision", "decision"])
        for rank, g in enumerate(groups, start=1):
            covered += g.mentions
            parts = " | ".join(multi_parts(g.key))
            for i, m in enumerate(g.members):
                status = (m.category if m.category in (CONFLICT, SPLIT) else "yes") \
                    if m.mapped else ""
                w.writerow([rank, g.key, g.mentions, f"{covered / total:.4f}",
                            len(g.members), m.name_th, m.n_recipes,
                            *(m.by_source.get(s, 0) for s in sources), status,
                            "" if m.category in (CONFLICT, SPLIT) else (m.canonical_id or ""),
                            parts if i == 0 else "", "", ""])


def summary(groups: list[Group]) -> list[str]:
    unmapped = [g for g in groups if not all(m.mapped for m in g.members)]
    strings = sum(len(g.members) for g in groups)
    lines = [f"{strings} strings in {len(groups)} suggested groups "
             f"({len(unmapped)} groups with unmapped strings)"]
    for share in (0.5, 0.8, 0.9):
        n = groups_to_reach(groups, share)
        lines.append(f"  {share:.0%} of mentions: first {n} groups "
                     f"({sum(len(g.members) for g in groups[:n])} strings)")
    lines.append(f"  flagged multi (HD-6 Q5, needs a split): "
                 f"{sum(1 for g in groups if multi_parts(g.key))} groups")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    with get_connection() as conn:
        conn.read_only = True
        rows = conn.execute(QUERY).fetchall()
        mapped = mapping_index(conn.execute(MAPPED_QUERY).fetchall())
    # The per-string `similar` column is not needed here; skipping it saves the O(n²)
    # comparison. Raw strings, as the lexicon maps them (HD-6 Q6 = (a)).
    worklist = build_worklist(rows, mapped, strip_quantities=False, with_similar=False)
    groups = group_worklist(worklist)
    write_csv(groups, args.out)
    print(f"wrote {args.out}")
    for line in summary(groups):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
