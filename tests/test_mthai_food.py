"""src/ingest/mthai_food.py — ingredient lists only, redacted, never loaded (HD-40 open).

Fixtures are synthetic and PII-free (tests/fixtures/mthai_food/sample.csv). The columns
that must never be read carry FIXTURE markers, so a leak is a substring check.
"""

from __future__ import annotations

import dataclasses
import json
import re
from datetime import date
from pathlib import Path

from scripts.parse_mthai import histogram, ingredient_set, provinces_named
from src.ingest.mthai_food import KEPT_FIELDS, parse_row, payload, read_csv
from src.ingest.pdpa import personal_data_classes

FIXTURE = Path(__file__).parent / "fixtures" / "mthai_food" / "sample.csv"
REPO = Path(__file__).resolve().parent.parent


def _all_text(record: object) -> str:
    return repr(dataclasses.asdict(record))  # type: ignore[call-overload]


def test_three_fixtures_parse() -> None:
    records = read_csv(FIXTURE)
    assert [r.post_id for r in records] == ["1", "2", "3"]


def test_dropped_columns_never_reach_a_record() -> None:
    for record in read_csv(FIXTURE):
        text = _all_text(record)
        for marker in ("AUTHOR-FIXTURE", "INTRO-FIXTURE", "METHOD-FIXTURE", "CREDIT-FIXTURE"):
            assert marker not in text
    assert set(KEPT_FIELDS).isdisjoint({"author", "intro", "method", "credited_source"})


def test_fixtures_are_pii_free_and_need_no_redaction() -> None:
    for record in read_csv(FIXTURE):
        assert record.redaction.total == 0
        # The source URL is kept by design (as in every loader) and is not personal data.
        for text in (record.title, *record.tags, *record.ingredient_lines):
            assert personal_data_classes(text) == [], text


def test_lines_tags_and_dates() -> None:
    first, second, third = read_csv(FIXTURE)
    assert first.ingredient_lines == ["กุ้ง 300 กรัม", "ตะไคร้ 2 ต้น", "ใบมะกรูด 5 ใบ",
                                      "น้ำปลา 2 ช้อนโต๊ะ"]  # blank line dropped
    assert first.tags == ["ต้มยำ", "อาหารไทย"]
    assert first.published_at == date(2024, 1, 2)
    assert second.tags == ["ส้มตำ", "เชียงใหม่"]
    assert third.published_at is None and third.tags == []
    # Section headings stay as lines, in page order (module docstring).
    assert third.ingredient_lines[0] == "ส่วนผสมตัวแป้ง"


def test_personal_data_in_a_kept_field_is_redacted_and_counted() -> None:
    row = {"record_id": "x", "post_id": "9", "url": "u", "title": "t",
           "publish_date": "", "tags": "",
           "ingredients": "กุ้ง 300 กรัม\nสั่งได้ที่ 081-234-5678"}
    record = parse_row(row)
    assert record.redaction.n_phone_numbers == 1
    assert "081-234-5678" not in _all_text(record)


def test_ingredient_sets_with_and_without_stripping() -> None:
    lines = ["กุ้ง 300 กรัม", "กุ้ง 200 กรัม", "ตะไคร้"]
    assert ingredient_set(lines, strip=False) == {"กุ้ง 300 กรัม", "กุ้ง 200 กรัม", "ตะไคร้"}
    assert ingredient_set(lines, strip=True) == {"กุ้ง", "ตะไคร้"}


def test_histogram_puts_one_in_the_last_bin() -> None:
    bins = dict(histogram([0.0, 0.95, 1.0, 0.5]))
    assert bins["[0.90, 1.00]"] == 2 and bins["[0.00, 0.10)"] == 1 and bins["[0.50, 0.70)"] == 1


def test_the_parser_never_writes() -> None:
    write = re.compile(r"\b(INSERT|UPDATE|DELETE|COPY)\b", re.IGNORECASE)
    assert not write.search((REPO / "src/ingest/mthai_food.py").read_text(encoding="utf-8"))


def test_the_report_path_writes_nothing() -> None:
    """Writes live only in load(), reached only with --load."""
    src = (REPO / "scripts/parse_mthai.py").read_text(encoding="utf-8")
    report = src[src.index("def main()"):]
    assert "INSERT" not in report and "if args.load:" in report


def test_hd22_rule_single_section_posts_only() -> None:
    first, _, third = read_csv(FIXTURE)
    assert first.is_single_section
    assert third.n_sections == 2 and not third.is_single_section


def test_payload_has_the_kapook_shape_and_no_dropped_fields() -> None:
    first = read_csv(FIXTURE)[0]
    data = payload(first)
    assert data["title_th"] == first.title
    assert data["category_source"] == "ต้มยำ | อาหารไทย"
    assert data["sections"] == [{"heading": None, "items": first.ingredient_lines}]
    assert "AUTHOR-FIXTURE" not in repr(data) and "METHOD-FIXTURE" not in repr(data)


def test_province_names_are_found_inside_compound_tags() -> None:
    first, second, _ = read_csv(FIXTURE)
    names = {"เชียงใหม่", "ชัยนาท"}
    assert provinces_named(second, names) == {"เชียงใหม่"}
    assert provinces_named(first, names) == set()


# ── HD-39: the state-promotional parsers (src/ingest/state_promotional.py) ─────────

_STATE = Path(__file__).parent / "fixtures" / "state_promotional"


def test_state_parsers_read_only_their_fields_and_drop_venue_and_page_text() -> None:
    from src.ingest.state_promotional import payload, read_mc, read_tat
    tat = read_tat(_STATE / "tat_food.csv")
    mc = read_mc("newline", _STATE / "dishes.csv")
    for rec in [*tat, *mc]:
        dumped = json.dumps(payload(rec), ensure_ascii=False)
        for marker in ("VENUE-FIXTURE", "NOTE-FIXTURE", "DISTRICT-FIXTURE", "OFFICE-FIXTURE"):
            assert marker not in dumped


def test_tat_rows_split_on_semicolons_and_fall_back_to_the_english_name() -> None:
    from src.ingest.state_promotional import read_tat
    a, b, c = read_tat(_STATE / "tat_food.csv")
    assert a.ingredient_lines == ["ข่า", "ตะไคร้", "พริก"] and a.list_kind == "campaign"
    assert b.name == "Fixture Noodles" and b.dish_th == "" and b.has_ingredients
    assert not c.has_ingredients and c.listed_province_th == "น่าน"


def test_mculture_redacts_before_splitting_so_a_phone_number_is_never_cut() -> None:
    from src.ingest.pdpa import find_leaks
    from src.ingest.state_promotional import SPLITS, read_mc
    for how in SPLITS:
        rec = read_mc(how, _STATE / "dishes.csv")[0]
        assert rec.redaction.n_phone_numbers == 1, how
        assert not any(find_leaks(x) for x in rec.ingredient_lines), how
        assert not any("089" in x for x in rec.ingredient_lines), how
    assert read_mc("delimiters", _STATE / "dishes.csv")[0].ingredient_lines[:3] == [
        "วัตถุดิบการทำอาหาร", "ประกอบด้วย ผักหวาน", "ไข่มดแดง ใบแมงลัก"]
    rows = read_mc("newline", _STATE / "dishes.csv")
    assert rows[2].duplicate_of == "9:2" and rows[0].key == "9:1"


def test_mculture_split_is_undecided_so_no_mculture_recipe_loads() -> None:
    from src.ingest import state_promotional
    assert state_promotional.MC_SPLIT is None


def test_tat_confidence_follows_the_researchers_rule() -> None:
    from scripts.parse_state_promo import confidence
    assert confidence("restaurant_guide") == "medium"
    for kind in ("campaign", "signature_dish", "dessert_guide"):
        assert confidence(kind) == "high"


def test_hd41_candidates_need_both_thresholds_strictly() -> None:
    from scripts.parse_state_promo import candidates
    s = frozenset
    sets = {1: s("abcdefg"), 2: s("abcdefg"), 3: s("abcdefg"), 4: s("abcdefgh")}
    titles = {1: "แกงส้มปลา", 2: "แกงส้มปลา", 3: "ขนมครก", 4: "แกงส้มปลา"}
    pairs = candidates(sets, titles, focus={1})
    assert [(a, b) for a, b, _, _ in pairs] == [(1, 2), (1, 4)]   # 3: title too far
    assert all(j > 0.85 and t > 0.8 for _, _, j, t in pairs)


def test_state_urls_keep_their_text_and_lose_only_flagged_substrings() -> None:
    """`redact` would blank every URL; a URL keeps its text and loses only what
    `find_leaks` (the database scan's check) flags."""
    from src.ingest.pdpa import RedactionReport, find_leaks
    from src.ingest.state_promotional import _clean_url
    r = RedactionReport()
    plain = "https://thai.tourismthailand.org/Articles/explore-thai-taste"
    assert _clean_url(plain, r) == plain and r.total == 0
    flagged = "https://thai.tourismthailand.org/Articles/ร้านอร่อย-ย่านถนนสิโรรส"
    out = _clean_url(flagged, r)
    assert out.startswith("https://thai.tourismthailand.org/Articles/ร้านอร่อย-ย่าน")
    assert "[REDACTED]" in out and not find_leaks(out) and r.n_addresses == 1
