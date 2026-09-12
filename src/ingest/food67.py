"""Parse `flavormap_food67.csv` — the 2567 (BE) one-province-one-menu book, already
extracted into a structured CSV by a process this repository has no record of.

**Provenance is unresolved, not assumed.** The only trace of "food67" anywhere in this
repository's history is commit `b8a90d6` (2026-08-16), which probed
`https://food.culture.go.th/bookfood67/` and found a FlipBuilder-rendered volume — a
single digitised flipbook, structurally unlike `food68`'s 231 discrete per-dish
PDFs — and explicitly did not parse it: "Extension probes, reported not parsed." No
script, commit, or decision entry in this repository produced `flavormap_food67.csv`.
See `docs/decisions.md` for the full note this requires per the brief's Task 0c.

**Column contract.** 14 fields, UTF-8 with a BOM (`encoding='utf-8-sig'`), ingredients
pipe-delimited (`|`) within `ingredients_th`. :func:`validate_columns` refuses to load
a file missing any of them rather than guessing which are present.

**Quality passes, each isolated so one bad row never stops the rest:**

- :func:`split_ingredients` / :func:`check_ingredient_count` — the `|`-split count
  must match the source's own `ingredient_count` field. A mismatch is reported, never
  silently trusted to either side.
- :func:`find_sara_am_corruption` / :func:`fix_sara_am_corruption` — the specific,
  well-documented PDF-extraction failure mode Bible §7.1 names (`น้ำ` losing its สระอำ
  during extraction). Corrected automatically **only** for the narrow, high-confidence
  case a bare, word-final "น้" reduces to — see the function docstring for why this is
  safe where a blanket regex would not be (Bible §7.1's own warning).
- :func:`find_dish_name_artifacts` — stray punctuation/spacing in dish names (a stray
  period before a parenthesis, an internal space that may be a delimiter artifact).
  **Never auto-corrected** — listed for human review, per the brief.
- :func:`split_khmer_gloss` — Surin's Khmer-language dish names carry a Thai gloss in
  parentheses (`อังแก๊บบ๊อบ (กบยัดไส้)`). Splits the pattern where it appears; leaves a
  name with no parenthetical untouched rather than guessing a gloss exists.
- :func:`flag_ingredient_variants` — frequency count plus a same-referent /
  granularity flag for likely-related ingredient strings, using
  `src.clean.dedupe.title_similarity` (the project's existing fuzzy-string measure,
  not a new one) for the spelling-variant case and substring containment for the
  granularity case. **Flags candidates; never merges them** — rule 4, HD-6.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.clean.dedupe import title_similarity

SOURCE_PROGRAMME = "one_province_one_menu_2567"
PROGRAMME_YEAR = 2567  # พ.ศ. (Buddhist Era), matching the source's own "food67" naming

REQUIRED_COLUMNS: tuple[str, ...] = (
    "dish_id",
    "dish_name_th",
    "province_th",
    "region_th",
    "book_page",
    "pdf_pages",
    "ingredients_th",
    "ingredient_count",
    "method_th",
    "method_step_count",
    "benefits_th",
    "history_th",
    "source_info_th",
    "source_url",
)

INGREDIENT_DELIMITER = "|"


def read_raw(path: Path) -> pd.DataFrame:
    """UTF-8 with a BOM, `dtype=str` throughout — this is a mixed prose/label/count
    file and pandas' numeric inference has no business touching any of it before
    validation has run."""
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)


def validate_columns(df: pd.DataFrame) -> None:
    missing = tuple(c for c in REQUIRED_COLUMNS if c not in df.columns)
    if missing:
        raise ValueError(f"expected column(s) missing from source CSV: {missing}")


# ── ingredient split + count validation ───────────────────────────────────────────

def split_ingredients(text: str | None) -> list[str]:
    """`ingredients_th` -> its tokens. Empty pieces (a leading/trailing/doubled `|`)
    are dropped rather than counted as an ingredient."""
    if not text:
        return []
    return [tok.strip() for tok in text.split(INGREDIENT_DELIMITER) if tok.strip()]


@dataclass
class CountMismatch:
    dish_id: str
    dish_name_th: str
    stated_count: str
    split_count: int


def check_ingredient_count(df: pd.DataFrame) -> list[CountMismatch]:
    """Every row where `len(split_ingredients(...))` disagrees with the source's own
    `ingredient_count` field. Neither field is trusted over the other — both are
    reported so a human can see which is wrong."""
    mismatches: list[CountMismatch] = []
    for _, row in df.iterrows():
        items = split_ingredients(row["ingredients_th"])
        stated = row["ingredient_count"]
        try:
            stated_int = int(stated)
        except (TypeError, ValueError):
            mismatches.append(
                CountMismatch(row["dish_id"], row["dish_name_th"], stated, len(items))
            )
            continue
        if stated_int != len(items):
            mismatches.append(
                CountMismatch(row["dish_id"], row["dish_name_th"], stated, len(items))
            )
    return mismatches


# ── sara am corruption (Bible §7.1) ────────────────────────────────────────────────

_THAI = "ก-๙"

#: A bare, word-final "น้" — Thai has no standalone word "น้"; it is always the head
#: of a longer syllable (น้ำ, น้อง, น้อย, ...). One not immediately continued by
#: another Thai-block character (a vowel sign, in every genuine case) is therefore
#: not a real word boundary — it is สระอำ having gone missing during extraction. Food
#: text specifically makes "น้ำ" overwhelmingly the dominant candidate for what was
#: lost, which is why this one case is corrected automatically rather than only
#: flagged — narrower and higher-confidence than a blanket "insert ำ" regex would be.
#:
#: The optional trailing `\s?` is part of the corruption span, not incidental
#: surrounding whitespace: the brief's own example is "น้ " (น้ followed by a space)
#: where "น้ำ" belongs — the space is สระอำ's dropped visual footprint, not a word
#: separator, so repairing this means consuming it, not leaving it stranded before
#: the next word.
_BARE_NAM = re.compile(rf"น้(?![{_THAI}])\s?")

#: The other shape Bible §7.1 names verbatim: "ประจำปี" extracting as "ประจ าปี" —
#: สระอำ's legacy two-glyph rendering (nikhahit + สระอา) losing the nikhahit and
#: gaining a spurious space, leaving "<consonant> า" where "<consonant>ำ" belongs, and
#: very often still mid-word (Bible's own example has "า" continuing straight into
#: "ปี" with no boundary) — so this pattern deliberately does NOT require a
#: non-Thai character after "า" the way :data:`_BARE_NAM` does. Reported only, never
#: auto-corrected: Bible §7.1 warns explicitly against a blanket regex here, because
#: a genuine "<word ending in a consonant> <word starting with า>" is not something
#: this pattern can rule out with the same confidence as :data:`_BARE_NAM` above.
_SPACED_SARA_AA = re.compile(rf"[{_THAI}]\s+า")


@dataclass
class SaraAmInstance:
    field: str
    row_id: str
    match: str
    context: str
    pattern: str  # "bare_nam" | "spaced_sara_aa"


def find_sara_am_corruption(text: str, *, field_name: str, row_id: str) -> list[SaraAmInstance]:
    if not text:
        return []
    found: list[SaraAmInstance] = []
    for m in _BARE_NAM.finditer(text):
        ctx = text[max(0, m.start() - 10) : m.end() + 10]
        found.append(SaraAmInstance(field_name, row_id, m.group(0), ctx, "bare_nam"))
    for m in _SPACED_SARA_AA.finditer(text):
        ctx = text[max(0, m.start() - 10) : m.end() + 10]
        found.append(SaraAmInstance(field_name, row_id, m.group(0), ctx, "spaced_sara_aa"))
    return found


def fix_sara_am_corruption(text: str) -> tuple[str, int]:
    """Corrects only the `_BARE_NAM` case (น้ -> น้ำ). Returns the corrected text and
    how many corrections were made. The `_SPACED_SARA_AA` case is deliberately left
    untouched here — see that pattern's own docstring."""
    fixed, n = _BARE_NAM.subn("น้ำ", text)
    return fixed, n


# ── dish-name artifacts (reported, never auto-corrected) ──────────────────────────

@dataclass
class DishNameArtifact:
    dish_id: str
    dish_name_th: str
    issue: str


#: A "." immediately before "(" — almost certainly an extraction artifact (a
#: sentence-final period from adjacent prose bleeding into the dish name field)
#: rather than genuine Thai orthography, which does not use periods this way.
_STRAY_PERIOD_BEFORE_PAREN = re.compile(r"\.\(")

#: An internal space inside what render as a single dish name is ambiguous: it may be
#: a genuine multi-word dish name, or a `|`-delimiter artifact that leaked into the
#: name field. Flagged, not corrected — telling the two apart needs a human who can
#: read the name.
_INTERNAL_SPACE = re.compile(r"[ก-๙]\s+[ก-๙]")


def find_dish_name_artifacts(df: pd.DataFrame) -> list[DishNameArtifact]:
    artifacts: list[DishNameArtifact] = []
    for _, row in df.iterrows():
        name = row["dish_name_th"]
        if not name:
            continue
        if _STRAY_PERIOD_BEFORE_PAREN.search(name):
            artifacts.append(
                DishNameArtifact(row["dish_id"], name, "stray period before parenthesis")
            )
        if _INTERNAL_SPACE.search(name):
            artifacts.append(
                DishNameArtifact(
                    row["dish_id"], name, "internal space (possible delimiter artifact)"
                )
            )
    return artifacts


# ── Khmer name / Thai gloss split (Surin) ──────────────────────────────────────────

@dataclass
class KhmerGloss:
    dish_id: str
    khmer_name: str
    thai_gloss: str


#: A name, then a parenthesised gloss, with nothing trailing after the close-paren.
#: Anchored to the whole field so a parenthetical elsewhere in a longer name (rare,
#: but possible) does not false-match.
_NAME_WITH_GLOSS = re.compile(r"^(?P<name>[^()]+?)\s*\((?P<gloss>[^()]+)\)\s*$")


def split_khmer_gloss(dish_id: str, dish_name_th: str) -> KhmerGloss | None:
    """Splits `name (gloss)` into its two parts. Returns None for a name with no
    parenthetical — never invents a gloss that is not there."""
    m = _NAME_WITH_GLOSS.match(dish_name_th or "")
    if not m:
        return None
    return KhmerGloss(dish_id, m.group("name").strip(), m.group("gloss").strip())


# ── ingredient variant flagging (lexicon seed, HD-6) ───────────────────────────────

SPELLING_VARIANT = "possible_spelling_variant"
GRANULARITY_RELATION = "possible_granularity_relation"

#: title_similarity (difflib ratio) above this, on strings of comparable length, is
#: the spelling-variant signal — reusing the project's existing fuzzy-string measure
#: (src.clean.dedupe) rather than inventing a second one.
SPELLING_SIMILARITY_THRESHOLD = 0.75

#: A length ratio floor alongside the similarity threshold: "น้ำตาล" vs
#: "น้ำตาลทราย" scores reasonably on raw character overlap despite being a
#: granularity relation, not a spelling variant — the length check keeps that pair
#: out of the spelling-variant bucket so it lands in the granularity one instead.
MAX_LENGTH_RATIO_FOR_SPELLING = 1.3


@dataclass
class VariantCandidate:
    a: str
    b: str
    count_a: int
    count_b: int
    relation: str
    score: float


def flag_ingredient_variants(frequencies: dict[str, int]) -> list[VariantCandidate]:
    """Pairwise-compares every distinct ingredient string against every other and
    flags two kinds of candidate relation, kept distinct because they are different
    decisions:

    - **spelling variant** (`SPELLING_VARIANT`): probably the same referent written
      two ways, e.g. แป้งข้าวเจ้า / แป้งข้าวจ้าว.
    - **granularity relation** (`GRANULARITY_RELATION`): one string is a qualified
      form of the other (a prefix/substring relation), e.g. น้ำตาล / น้ำตาลทราย /
      น้ำตาลมะพร้าว, or พริก / พริกขี้หนู — a decision about lexicon *granularity*,
      not a spelling correction, and the brief is explicit these are not the same
      kind of call.

    Nothing here merges anything. Output is a flat list of candidate pairs, ordered
    by combined frequency, for a human to route into `alias_candidates` once HD-6
    seeds `canonical_ingredients` (this function's output cannot be written to
    `alias_candidates` before that: the table's `canonical_id` is `NOT NULL REFERENCES
    canonical_ingredients`, which is empty until then).
    """
    items = sorted(frequencies.items(), key=lambda kv: (-kv[1], kv[0]))
    candidates: list[VariantCandidate] = []
    seen: set[tuple[str, str]] = set()

    for i, (a, count_a) in enumerate(items):
        for b, count_b in items[i + 1 :]:
            key = (a, b) if a < b else (b, a)
            if key in seen:
                continue

            if a in b or b in a:
                shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
                if shorter != longer:
                    seen.add(key)
                    candidates.append(
                        VariantCandidate(
                            a, b, count_a, count_b, GRANULARITY_RELATION,
                            len(shorter) / len(longer),
                        )
                    )
                    continue

            length_ratio = max(len(a), len(b)) / max(1, min(len(a), len(b)))
            if length_ratio > MAX_LENGTH_RATIO_FOR_SPELLING:
                continue
            score = title_similarity(a, b)
            if score >= SPELLING_SIMILARITY_THRESHOLD:
                seen.add(key)
                candidates.append(VariantCandidate(a, b, count_a, count_b, SPELLING_VARIANT, score))

    candidates.sort(key=lambda c: -(c.count_a + c.count_b))
    return candidates


def ingredient_frequencies(df: pd.DataFrame) -> dict[str, int]:
    freq: dict[str, int] = {}
    for _, row in df.iterrows():
        for item in split_ingredients(row["ingredients_th"]):
            freq[item] = freq.get(item, 0) + 1
    return freq


# ── whole-file report ──────────────────────────────────────────────────────────────

@dataclass
class QualityReport:
    total_rows: int
    count_mismatches: list[CountMismatch] = field(default_factory=list)
    sara_am_instances: list[SaraAmInstance] = field(default_factory=list)
    dish_name_artifacts: list[DishNameArtifact] = field(default_factory=list)
    null_method_rows: list[str] = field(default_factory=list)
    null_benefits_rows: list[str] = field(default_factory=list)
    khmer_glosses: list[KhmerGloss] = field(default_factory=list)
    top_ingredients: list[tuple[str, int]] = field(default_factory=list)
    variant_candidates: list[VariantCandidate] = field(default_factory=list)


TEXT_FIELDS_TO_SCAN_FOR_SARA_AM = (
    "dish_name_th",
    "ingredients_th",
    "method_th",
    "benefits_th",
    "history_th",
)


def build_quality_report(df: pd.DataFrame, *, top_n: int = 100) -> QualityReport:
    validate_columns(df)

    report = QualityReport(total_rows=len(df))
    report.count_mismatches = check_ingredient_count(df)
    report.dish_name_artifacts = find_dish_name_artifacts(df)

    for _, row in df.iterrows():
        for field_name in TEXT_FIELDS_TO_SCAN_FOR_SARA_AM:
            report.sara_am_instances.extend(
                find_sara_am_corruption(
                    row[field_name], field_name=field_name, row_id=row["dish_id"]
                )
            )
        if not row["method_th"]:
            report.null_method_rows.append(row["dish_id"])
        if not row["benefits_th"]:
            report.null_benefits_rows.append(row["dish_id"])
        gloss = split_khmer_gloss(row["dish_id"], row["dish_name_th"])
        if gloss is not None:
            report.khmer_glosses.append(gloss)

    freq = ingredient_frequencies(df)
    report.top_ingredients = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]
    report.variant_candidates = flag_ingredient_variants(freq)

    return report
