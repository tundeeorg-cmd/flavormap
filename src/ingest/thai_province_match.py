"""Word-boundary-aware Thai province matching — Task 1 of the `datago_catalog` brief.

**The bug, confirmed against real data.** `flavormap_datago_catalog.csv`'s `province`
column holds 106 distinct values against Thailand's 77 real provinces. The worst
confirmed case: a dataset titled "เรือประมงนอกน่านน้ำ..." (deep-sea fishing vessels
outside **น่านน้ำ**, territorial waters) is assigned `province='น่าน'` — Nan, a
landlocked province — because a naive substring check found "น่าน" inside "น่านน้ำ".
The same class of error is documented for "แพร่" matching inside "เผยแพร่"
(published). Thai has no spaces between words, so `str.contains` is wrong by
construction for this.

**Verified fix.** PyThaiNLP's `newmm` tokenizer splits both traps correctly as single
dictionary words — `word_tokenize('เรือประมงนอกน่านน้ำ')` yields `['เรือประมง', 'นอก',
'น่านน้ำ', ...]`, never `'น่าน'` as its own token; `word_tokenize('เผยแพร่ข้อมูล')`
yields `['เผยแพร่', 'ข้อมูล']`, never `'แพร่'` on its own. Matching against **whole
tokens** rather than substrings resolves both traps and every case of the same shape,
empirically confirmed rather than assumed — see `tests/test_thai_province_match.py`.

**Task 1b asked for three options evaluated, not silently one chosen** — all three
are implemented here so the comparison in `docs/decisions.md` is against real
behaviour, not a description of hypothetical trade-offs:

- :func:`tokens_containing_official_province` — **option (b)**, newmm whole-token
  matching against the official 77-province list. The one this module recommends and
  uses as its default "corrected" matcher — it needs no source-specific maintenance
  and is verified against the two known traps plus the rest of the province list.
- :data:`KNOWN_TRAP_SUBSTRINGS` / :func:`contains_known_trap` — **option (c)**, an
  explicit blocklist. Cheap, but incomplete by construction: it only catches traps
  someone has already found. Kept as a defense-in-depth cross-check, not the primary
  method.
- Option (a), "trust a structured field where the source provides one, else leave
  null", is not implementable from this CSV alone — nothing in it distinguishes a
  province value that came from data.go.th's own structured metadata field from one
  a text-matching step backfilled. Noted as unavailable rather than skipped silently.

**What this module does NOT do:** decide which of the three is *the* project's
method going forward, or silently correct `province` in place. `check_assignment`
reports a verdict per row; nothing here rewrites a table.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pythainlp.tokenize import word_tokenize

from src.config import REFERENCE_DIR

PROVINCES_CSV = REFERENCE_DIR / "provinces.csv"

#: A handful of confirmed or highly plausible trap substrings — option (c). NOT
#: exhaustive: found by inspection of this one file's 106 distinct values plus the
#: brief's own two examples, not by any systematic search of Thai vocabulary. Its
#: incompleteness is the argument for preferring option (b) as the primary matcher,
#: not a defect to silently patch by adding more entries piecemeal.
KNOWN_TRAP_SUBSTRINGS: dict[str, tuple[str, ...]] = {
    "น่าน": ("น่านน้ำ",),
    "แพร่": ("เผยแพร่", "แพร่กระจาย", "แพร่หลาย"),
    "ตาก": ("ตากอากาศ", "ตากแห้ง", "ผึ่งตาก"),
    "เลย": (),  # "เลย" ("at all"/"beyond") is common enough that a substring
                # blocklist cannot enumerate its false-positive contexts; flagged as
                # a name this method is least trustworthy for, not fixed here.
}


@lru_cache(maxsize=1)
def official_provinces() -> frozenset[str]:
    """The 77 real names, from this project's own reference data — not re-derived
    or hand-typed here, so it can never drift from `data/reference/provinces.csv`."""
    import csv

    with PROVINCES_CSV.open(encoding="utf-8") as fh:
        return frozenset(row["name_th"] for row in csv.DictReader(fh))


def tokens_containing_official_province(text: str | None) -> set[str]:
    """Option (b) — every official province name appearing as a **whole token** in
    `text`'s newmm tokenisation. Empty text yields an empty set, never a guess."""
    if not text:
        return set()
    provinces = official_provinces()
    tokens = word_tokenize(text, engine="newmm")
    return {t for t in tokens if t in provinces}


def contains_known_trap(province: str, text: str | None) -> str | None:
    """Option (c) — is `province` present in `text` only via one of its known trap
    substrings? Returns the matched trap string, or None. Only meaningful for
    provinces with an entry in :data:`KNOWN_TRAP_SUBSTRINGS`."""
    if not text:
        return None
    for trap in KNOWN_TRAP_SUBSTRINGS.get(province, ()):
        if trap in text:
            return trap
    return None


# ── per-row verdicts (Task 1c: quantify the damage) ────────────────────────────────

VERDICT_CONFIRMED = "confirmed_match"        # province is a whole token in the text
VERDICT_TRAP_MISMATCH = "trap_mismatch"      # a known substring trap explains the value
VERDICT_NO_EVIDENCE = "no_textual_evidence"  # valid province name, but text doesn't support it
VERDICT_INVALID_VALUE = "invalid_value"      # not one of the 77 official names at all
VERDICT_EMPTY = "empty"                      # no province assigned


@dataclass
class ProvinceCheckResult:
    original_value: str
    verdict: str
    evidence: str | None = None  # the trap substring, when verdict is trap_mismatch


def check_assignment(
    province_value: str | None, title: str, description: str = ""
) -> ProvinceCheckResult:
    """Task 1c's per-row check: does the existing `province` value hold up against
    the corrected (option-b) matcher run on this row's own title/description text?

    Deliberately three-way, not binary — see the module docstring. A province with no
    textual evidence either way is reported as unverifiable, not asserted wrong: it
    may be entirely correct and simply sourced from a structured field this CSV gives
    no way to see.
    """
    value = (province_value or "").strip()
    if not value:
        return ProvinceCheckResult(value, VERDICT_EMPTY)

    if value not in official_provinces():
        return ProvinceCheckResult(value, VERDICT_INVALID_VALUE)

    combined = f"{title} {description}"
    if value in tokens_containing_official_province(combined):
        return ProvinceCheckResult(value, VERDICT_CONFIRMED)

    trap = contains_known_trap(value, combined)
    if trap:
        return ProvinceCheckResult(value, VERDICT_TRAP_MISMATCH, evidence=trap)

    return ProvinceCheckResult(value, VERDICT_NO_EVIDENCE)
