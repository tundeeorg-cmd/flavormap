"""Hand-transcribed DCP forms (HD-35): src/ingest/dcp_manual.py, scripts/load_dcp_manual.py.

Database tests use the made-up document names east_98_9 / east_99_9, which no real form
has, and a temporary corpus directory holding an empty stand-in PDF. They create the
Nakhon Nayok province row only if it is missing, so they run on a fresh database too.
Person-shaped values are invented (ทดสอบ), as in tests/test_pdpa.py.
"""

from __future__ import annotations

import datetime
import hashlib
from collections.abc import Iterator
from pathlib import Path

import pytest

from scripts.load_dcp_manual import MANUAL_DIR, load, read_all
from src.db import get_connection
from src.ingest.dcp_manual import (
    INGREDIENT_KEYS,
    RECORD_KEYS,
    ManualError,
    manual_files,
    parse_manual,
)
from src.ingest.pdpa import find_leaks
from tests.test_pdpa import test_no_personal_data_in_any_table as scan_every_table

D = datetime.date


def _valid(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "dish_name_th": "แกงทดสอบ", "province_th": "นครนายก", "district_th": "เมือง",
        "dish_category_source": "อาหารคาว", "occasion_th": "ประจำ",
        "endangerment": "near_lost", "transcribed_on": D(2026, 10, 6),
        "ingredients": [
            {"name_th": "หอมแดง", "quantity_value": "3", "quantity_unit": "หัว",
             "acquisition_raw": "ปลูกเอง"},
            {"name_th": "ตะไคร้"},
        ],
    }
    base.update(over)
    return base


# ── parse ─────────────────────────────────────────────────────────────────────

def test_a_valid_transcription_parses_into_the_parsers_fields() -> None:
    rec = parse_manual("east_5_1", _valid())
    assert rec.document_ref == "east_5_1.pdf"
    assert (rec.dish_category, rec.occasion) == ("savoury", "everyday")  # parser's tables
    assert [i.position for i in rec.ingredients] == [1, 2]
    assert rec.ingredients[0].acquisition_raw == "ปลูกเอง"


def test_there_is_no_field_for_a_person() -> None:
    allowed = RECORD_KEYS | INGREDIENT_KEYS
    for word in ("name_th",):  # the dish's / ingredient's Thai name, not a person's
        assert word in allowed
    assert not any(k in allowed for k in ("informant", "submitter", "phone", "address",
                                          "postcode", "house", "road", "email"))


@pytest.mark.parametrize("bad_key", ["informant_name", "submitter", "phone", "address",
                                     "postcode", "subdistrict", "ตำบล", "signature"])
def test_a_person_or_contact_key_is_refused_by_design(bad_key: str) -> None:
    with pytest.raises(ManualError, match="no such field, by design"):
        parse_manual("east_5_1", _valid(**{bad_key: "x"}))


@pytest.mark.parametrize("pii", ["นางสมหญิง ทดสอบ", "โทร 08 1234 5678",
                                 "เลขที่ ๙๙/๙ หมู่ ๖", "ทดสอบ@example.com"])
@pytest.mark.parametrize("field", ["dish_name_th", "district_th", "notes", "ingredient",
                                   "acquisition_raw"])
def test_personal_data_in_any_text_is_refused_and_never_echoed(pii: str, field: str) -> None:
    data = _valid()
    rows = [dict(r) for r in data["ingredients"]]  # type: ignore[union-attr]
    if field == "ingredient":
        rows[0]["name_th"] = pii
    elif field == "acquisition_raw":
        rows[0]["acquisition_raw"] = pii
    else:
        data[field] = pii
    data["ingredients"] = rows
    with pytest.raises(ManualError, match="contains personal data") as exc:
        parse_manual("east_5_1", data)
    assert not find_leaks(str(exc.value))


@pytest.mark.parametrize(
    ("over", "message"),
    [
        ({"province_th": ""}, "never the §1.3 address"),
        ({"dish_name_th": None}, "dish_name_th is required"),
        ({"transcribed_on": "2026-10-06"}, "transcribed_on is required"),
        ({"ingredients": []}, "at least one"),
        ({"dish_category_source": "savoury"}, "dish_category_source must be one of"),
        ({"occasion_th": "daily"}, "occasion_th must be one of"),
        ({"endangerment": "other"}, "endangerment must be one of"),
        ({"acquisition_mode": "grown"}, "unknown key 'acquisition_mode'"),
    ],
)
def test_invalid_transcriptions_are_refused(over: dict[str, object], message: str) -> None:
    data = {k: v for k, v in _valid(**over).items() if v is not None}
    with pytest.raises(ManualError, match=message):
        parse_manual("east_5_1", data)


def test_the_file_name_must_be_a_dcp_document() -> None:
    with pytest.raises(ManualError, match="file name must be the DCP document's"):
        parse_manual("nakhon_nayok_1", _valid())


def test_unticked_boxes_stay_unknown() -> None:
    rec = parse_manual("east_5_1", {k: v for k, v in _valid().items()
                                    if k not in ("dish_category_source", "occasion_th",
                                                 "endangerment")})
    assert (rec.dish_category, rec.occasion, rec.endangerment) == (None, None, None)


def test_template_documents_every_key_and_is_skipped() -> None:
    text = (MANUAL_DIR / "_template.toml").read_text(encoding="utf-8")
    assert not [k for k in RECORD_KEYS | INGREDIENT_KEYS if k not in text]
    assert all(not p.name.startswith("_") for p in manual_files(MANUAL_DIR))


def test_real_transcriptions_on_disk_are_valid_and_clean() -> None:
    for path in manual_files(MANUAL_DIR):
        assert not find_leaks(path.read_text(encoding="utf-8")), path.name
    read_all(MANUAL_DIR)


# ── database ──────────────────────────────────────────────────────────────────

DOC, PARSED_DOC = "east_99_9", "east_98_9"
_PARSED_SRC = "_test_manual_parsed_src"


def _q(sql: str, *params: object) -> list[tuple[object, ...]]:
    conn = get_connection()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


@pytest.fixture
def corpus(tmp_path: Path) -> Iterator[Path]:
    (tmp_path / f"{DOC}.pdf").write_bytes(b"%PDF-stand-in")
    (tmp_path / f"{PARSED_DOC}.pdf").write_bytes(b"%PDF-stand-in")
    conn = get_connection()
    created = conn.execute(
        """INSERT INTO provinces (province_code, name_th, name_en, region4,
                                 centroid_lat, centroid_lon)
           VALUES ('TH-26', 'นครนายก', 'Nakhon Nayok', 'Central', 14.2, 101.2)
           ON CONFLICT DO NOTHING RETURNING 1""").fetchone() is not None
    conn.commit()
    try:
        yield tmp_path
    finally:
        conn.rollback()
        for where, params in (
            ("rr.source_url = ANY(%s)", ([f"manual:{DOC}.pdf", f"manual:{PARSED_DOC}.pdf"],)),
            ("rr.source_id = %s", (_PARSED_SRC,)),
        ):
            conn.execute(f"""DELETE FROM province_attribution WHERE recipe_id IN (
                SELECT r.recipe_id FROM recipes r JOIN raw_recipes rr USING (raw_id)
                 WHERE {where})""", params)
            conn.execute(f"""DELETE FROM recipes WHERE raw_id IN (
                SELECT raw_id FROM raw_recipes rr WHERE {where})""", params)
            conn.execute(f"DELETE FROM raw_recipes rr WHERE {where}", params)
        conn.execute("DELETE FROM sources WHERE source_id = %s", (_PARSED_SRC,))
        if created:
            conn.execute("DELETE FROM provinces WHERE province_code = 'TH-26'")
        conn.commit()
        conn.close()


def test_a_load_writes_an_official_manual_record(corpus: Path) -> None:
    assert load([parse_manual(DOC, _valid())], corpus) == [f"{DOC}.pdf"]
    [(register, method, province, tier, confidence, parsed)] = _q(
        """SELECT r.register, r.extraction_method, pa.province_code, pa.tier, pa.confidence,
                  rr.parsed_json
             FROM recipes r JOIN raw_recipes rr USING (raw_id)
             JOIN province_attribution pa USING (recipe_id)
            WHERE rr.source_url = %s""", f"manual:{DOC}.pdf")
    assert (register, method, province, tier, confidence) == (
        "official", "manual", "TH-26", 1, "high")
    assert parsed["extraction_method"] == "manual"  # type: ignore[index]
    assert [i["name_th"] for i in parsed["ingredients"]] == ["หอมแดง", "ตะไคร้"]  # type: ignore[index]
    assert all("acquisition_mode" not in i for i in parsed["ingredients"])  # type: ignore[index]
    scan_every_table()


def test_reloading_an_edited_transcription_updates_in_place(corpus: Path) -> None:
    load([parse_manual(DOC, _valid())], corpus)
    load([parse_manual(DOC, _valid(endangerment="transmitted"))], corpus)
    assert _q("SELECT count(*) FROM raw_recipes WHERE source_url = %s",
              f"manual:{DOC}.pdf") == [(1,)]
    assert _q("""SELECT r.endangerment FROM recipes r JOIN raw_recipes rr USING (raw_id)
                  WHERE rr.source_url = %s""", f"manual:{DOC}.pdf") == [("transmitted",)]


def test_a_form_the_parser_already_loaded_is_refused(corpus: Path) -> None:
    conn = get_connection()
    try:
        conn.execute("""INSERT INTO sources (source_id, source_type, base_url, robots_ok,
                            audited_on) VALUES (%s, 'institutional', 'x', true, '2026-10-06')""",
                     (_PARSED_SRC,))
        raw = conn.execute(
            """INSERT INTO raw_recipes (source_id, source_url, raw_path, content_hash)
               VALUES (%s, 'x', %s, %s) RETURNING raw_id""",
            (_PARSED_SRC, f"/x/{PARSED_DOC}.pdf", hashlib.sha256(b"p").hexdigest()),
        ).fetchone()[0]  # type: ignore[index]
        conn.execute("""INSERT INTO recipes (raw_id, name_th, register, extraction_method)
                        VALUES (%s, 'ทดสอบ', 'official', 'parsed')""", (raw,))
        conn.commit()
    finally:
        conn.close()
    import scripts.load_dcp_manual as m

    original = m.SOURCE_ID
    m.SOURCE_ID = _PARSED_SRC  # the stand-in parsed row lives under the test source
    try:
        with pytest.raises(ManualError, match="already loaded this form"):
            load([parse_manual(PARSED_DOC, _valid())], corpus)
    finally:
        m.SOURCE_ID = original


def test_an_unknown_province_or_missing_pdf_loads_nothing(corpus: Path) -> None:
    with pytest.raises(ManualError, match="matches no province name"):
        load([parse_manual(DOC, _valid(province_th="ทดสอบจังหวัด"))], corpus)
    with pytest.raises(ManualError, match="no such PDF"):
        load([parse_manual("east_97_9", _valid())], corpus)
    assert _q("SELECT count(*) FROM raw_recipes WHERE source_url LIKE %s",
              "manual:east_9%") == [(0,)]
