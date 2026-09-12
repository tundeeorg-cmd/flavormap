"""`src/ingest/food67.py` — ingredient split/count validation, sara-am corruption,
dish-name artifacts, Khmer/gloss splitting, and ingredient-variant flagging.

Every example below is either lifted verbatim from the task brief (the brief quotes
specific corrupted strings, artifact dish names, Surin Khmer names, and ingredient
variant pairs directly) or built from Bible §7.1's own documented corruption example.
None of it is drawn from the real `flavormap_food67.csv`, which this project does not
have a copy of — see `docs/decisions.md`'s Task 0 note.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.ingest.food67 import (
    GRANULARITY_RELATION,
    REQUIRED_COLUMNS,
    SPELLING_VARIANT,
    build_quality_report,
    check_ingredient_count,
    find_dish_name_artifacts,
    find_sara_am_corruption,
    fix_sara_am_corruption,
    flag_ingredient_variants,
    ingredient_frequencies,
    split_ingredients,
    split_khmer_gloss,
    validate_columns,
)

# ── ingredient split + count validation ─────────────────────────────────────────

def test_split_ingredients_basic() -> None:
    assert split_ingredients("ไก่|ตะไคร้|ข่า") == ["ไก่", "ตะไคร้", "ข่า"]


def test_split_ingredients_drops_empty_pieces() -> None:
    assert split_ingredients("ไก่||ตะไคร้|") == ["ไก่", "ตะไคร้"]


@pytest.mark.parametrize("value", [None, ""])
def test_split_ingredients_empty_field(value: str | None) -> None:
    assert split_ingredients(value) == []


def _df(rows: list[dict[str, str]]) -> pd.DataFrame:
    base = {c: "" for c in REQUIRED_COLUMNS}
    return pd.DataFrame([{**base, **r} for r in rows])


def test_check_ingredient_count_matches() -> None:
    df = _df([{"dish_id": "D1", "dish_name_th": "x", "ingredients_th": "ไก่|ตะไคร้",
               "ingredient_count": "2"}])
    assert check_ingredient_count(df) == []


def test_check_ingredient_count_flags_mismatch() -> None:
    df = _df([{"dish_id": "D1", "dish_name_th": "x", "ingredients_th": "ไก่|ตะไคร้",
               "ingredient_count": "3"}])
    mismatches = check_ingredient_count(df)
    assert len(mismatches) == 1
    assert mismatches[0].dish_id == "D1"
    assert mismatches[0].split_count == 2
    assert mismatches[0].stated_count == "3"


def test_check_ingredient_count_flags_unparseable_stated_count() -> None:
    df = _df([{"dish_id": "D1", "dish_name_th": "x", "ingredients_th": "ไก่",
               "ingredient_count": "n/a"}])
    mismatches = check_ingredient_count(df)
    assert len(mismatches) == 1


def test_validate_columns_raises_on_missing() -> None:
    with pytest.raises(ValueError):
        validate_columns(pd.DataFrame([{"dish_id": "D1"}]))


def test_validate_columns_passes_on_full_set() -> None:
    validate_columns(_df([{"dish_id": "D1"}]))


# ── sara am corruption ────────────────────────────────────────────────────────────

def test_bare_nam_detected_in_brief_example() -> None:
    """The brief's own example: a bare 'น้' where 'น้ำ' is expected."""
    text = "ใส่น้ ปลาลงไป"
    hits = find_sara_am_corruption(text, field_name="method_th", row_id="D1")
    assert any(h.pattern == "bare_nam" for h in hits)


def test_bare_nam_not_flagged_for_genuine_words() -> None:
    """น้ำ, น้อง, น้อย all continue with a Thai vowel — none should be flagged."""
    for word in ("น้ำปลา", "น้องสาว", "น้อยหน่า"):
        assert find_sara_am_corruption(word, field_name="x", row_id="D1") == []


def test_fix_sara_am_corruption_repairs_bare_nam() -> None:
    fixed, n = fix_sara_am_corruption("ใส่น้ ปลาลงไป")
    assert fixed == "ใส่น้ำปลาลงไป"
    assert n == 1


def test_fix_sara_am_corruption_no_op_on_clean_text() -> None:
    fixed, n = fix_sara_am_corruption("น้ำปลา")
    assert fixed == "น้ำปลา"
    assert n == 0


def test_spaced_sara_aa_detected_but_not_corrected() -> None:
    """Bible §7.1's own example: 'ประจำปี' extracting as 'ประจ าปี'. Reported only —
    Bible explicitly warns against a blanket regex fix for this shape."""
    text = "รายงานประจ าปีของจังหวัด"
    hits = find_sara_am_corruption(text, field_name="history_th", row_id="D2")
    assert any(h.pattern == "spaced_sara_aa" for h in hits)
    fixed, n = fix_sara_am_corruption(text)
    assert fixed == text  # untouched
    assert n == 0


# ── dish-name artifacts (report only, never auto-corrected) ───────────────────────

def test_stray_period_before_parenthesis_flagged() -> None:
    df = _df([{"dish_id": "D3", "dish_name_th": "ไก่ทอดมะแขว่น.(ไก่ประดู่หางดำ)"}])
    artifacts = find_dish_name_artifacts(df)
    assert any(a.issue == "stray period before parenthesis" for a in artifacts)
    # Never corrected — the source string itself must survive untouched in the frame.
    assert df.iloc[0]["dish_name_th"] == "ไก่ทอดมะแขว่น.(ไก่ประดู่หางดำ)"


def test_internal_space_flagged() -> None:
    df = _df([{"dish_id": "D4", "dish_name_th": "แกงก้าม ขาหมู"}])
    artifacts = find_dish_name_artifacts(df)
    assert any(a.issue == "internal space (possible delimiter artifact)" for a in artifacts)


def test_ordinary_dish_name_not_flagged() -> None:
    df = _df([{"dish_id": "D5", "dish_name_th": "แกงส้ม"}])
    assert find_dish_name_artifacts(df) == []


# ── Khmer name / Thai gloss (Surin) ────────────────────────────────────────────────

SURIN_EXAMPLES = [
    ("S1", "นมเนียล", None),
    ("S2", "อังแก๊บบ๊อบ (กบยัดไส้)", ("อังแก๊บบ๊อบ", "กบยัดไส้")),
    ("S3", "สันลอเจก (แกงกล้วย)", ("สันลอเจก", "แกงกล้วย")),
    ("S4", "จรั้วะโดง (น้ำพริกกะทิ)", ("จรั้วะโดง", "น้ำพริกกะทิ")),
    ("S5", "อันซอมสะเลอะโดง", None),
]


@pytest.mark.parametrize("dish_id,name,expected", SURIN_EXAMPLES)
def test_split_khmer_gloss_on_brief_examples(
    dish_id: str, name: str, expected: tuple[str, str] | None
) -> None:
    result = split_khmer_gloss(dish_id, name)
    if expected is None:
        assert result is None
    else:
        assert result is not None
        assert (result.khmer_name, result.thai_gloss) == expected


def test_split_khmer_gloss_on_all_five_brief_names_counts_three_with_gloss() -> None:
    """The brief lists five Surin names; three carry a parenthetical Thai gloss."""
    results = [split_khmer_gloss(d, n) for d, n, _ in SURIN_EXAMPLES]
    assert sum(r is not None for r in results) == 3


# ── ingredient variant flagging ────────────────────────────────────────────────────

def test_spelling_variant_pair_flagged() -> None:
    freq = {"แป้งข้าวเจ้า": 14, "แป้งข้าวจ้าว": 11}
    candidates = flag_ingredient_variants(freq)
    assert len(candidates) == 1
    c = candidates[0]
    assert {c.a, c.b} == {"แป้งข้าวเจ้า", "แป้งข้าวจ้าว"}
    assert c.relation == SPELLING_VARIANT


def test_granularity_relation_flagged_not_spelling() -> None:
    freq = {"น้ำตาล": 40, "น้ำตาลทราย": 12, "น้ำตาลมะพร้าว": 8}
    candidates = flag_ingredient_variants(freq)
    assert candidates  # at least one pair flagged
    assert all(c.relation == GRANULARITY_RELATION for c in candidates)


def test_prik_granularity_pair() -> None:
    freq = {"พริก": 30, "พริกขี้หนู": 9}
    candidates = flag_ingredient_variants(freq)
    assert len(candidates) == 1
    assert candidates[0].relation == GRANULARITY_RELATION


def test_namman_granularity_pair() -> None:
    freq = {"น้ำมัน": 20, "น้ำมันพืช": 15}
    candidates = flag_ingredient_variants(freq)
    assert len(candidates) == 1
    assert candidates[0].relation == GRANULARITY_RELATION


def test_unrelated_ingredients_not_flagged() -> None:
    freq = {"ไก่": 20, "มะนาว": 15, "เกลือ": 10}
    assert flag_ingredient_variants(freq) == []


def test_flag_ingredient_variants_never_merges_just_flags() -> None:
    """The function's contract: candidates, never a merged/deduplicated frequency
    table. Both original strings must still be present in the output."""
    freq = {"แป้งข้าวเจ้า": 14, "แป้งข้าวจ้าว": 11}
    candidates = flag_ingredient_variants(freq)
    all_strings = {s for c in candidates for s in (c.a, c.b)}
    assert all_strings == set(freq)


# ── whole-file report ────────────────────────────────────────────────────────────

def _fixture_csv(tmp_path: Path) -> Path:
    rows = [
        {
            "dish_id": "D1",
            "dish_name_th": "แกงไก่",
            "province_th": "น่าน",
            "region_th": "ภาคเหนือ",
            "book_page": "18",
            "pdf_pages": "18",
            "ingredients_th": "ไก่|ตะไคร้|ข่า",
            "ingredient_count": "3",
            "method_th": "ผัดให้หอม",
            "method_step_count": "1",
            "benefits_th": "",
            "history_th": "รายงานประจ าปี",
            "source_info_th": "",
            "source_url": "https://food.culture.go.th/bookfood67/#p=18",
        },
        {
            "dish_id": "D2",
            "dish_name_th": "อังแก๊บบ๊อบ (กบยัดไส้)",
            "province_th": "สุรินทร์",
            "region_th": "ภาคตะวันออกเฉียงเหนือ",
            "book_page": "45",
            "pdf_pages": "45-46",
            "ingredients_th": "กบ|ตะไคร้",
            "ingredient_count": "1",  # deliberate mismatch
            "method_th": "",
            "method_step_count": "",
            "benefits_th": "ช่วยย่อยอาหาร",
            "history_th": "",
            "source_info_th": "",
            "source_url": "https://food.culture.go.th/bookfood67/#p=45",
        },
    ]
    path = tmp_path / "flavormap_food67_fixture.csv"
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def test_build_quality_report_end_to_end(tmp_path: Path) -> None:
    df = pd.read_csv(_fixture_csv(tmp_path), encoding="utf-8-sig", dtype=str, keep_default_na=False)
    report = build_quality_report(df)

    assert report.total_rows == 2
    assert len(report.count_mismatches) == 1
    assert report.count_mismatches[0].dish_id == "D2"

    assert any(s.pattern == "spaced_sara_aa" for s in report.sara_am_instances)

    assert report.null_benefits_rows == ["D1"]
    assert report.null_method_rows == ["D2"]

    assert len(report.khmer_glosses) == 1
    assert report.khmer_glosses[0].dish_id == "D2"

    freq = ingredient_frequencies(df)
    assert freq["ตะไคร้"] == 2
    assert freq["ไก่"] == 1
