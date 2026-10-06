"""Rules 4–7 of docs/scraping_rules.md — what a scraped record may carry.

Personal-data fixtures are INVENTED; surname ทดสอบ ("test") marks them as synthetic,
following tests/test_pdpa.py.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import UTC, date, datetime
from typing import Any

import pytest

from src.ingest.pdpa import find_leaks
from src.scrape.record import (
    ALLOWED_PAYLOAD_KEYS,
    Claim,
    RecordRefused,
    ScrapedRecipe,
    finalise,
    insert_raw_recipe,
)

NOW = datetime(2026, 10, 6, 3, 0, tzinfo=UTC)


def _rec(**kw: Any) -> ScrapedRecipe:
    base: dict[str, Any] = dict(
        url="https://new.example/recipe/1",
        title_th="แกงไตปลา สูตรภาคใต้",
        scraped_at=NOW,
        published_at=date(2025, 3, 1),
        site_category="อาหารใต้",
        site_tags=["แกง", "ภาคใต้"],
        region_claim=Claim("ภาคใต้", "title"),
        ingredient_lines=["ไตปลา 2 ช้อนโต๊ะ", "พริกแกง 1 ถ้วย", "ตามชอบ น้ำตาล"],
        servings="4 ที่",
    )
    base.update(kw)
    return ScrapedRecipe(**base)


def test_a_clean_record_carries_exactly_the_allowed_keys() -> None:
    fin = finalise(_rec())
    assert set(fin.payload) == ALLOWED_PAYLOAD_KEYS
    assert fin.payload["ingredient_lines"] == ["ไตปลา 2 ช้อนโต๊ะ", "พริกแกง 1 ถ้วย", "ตามชอบ น้ำตาล"]
    assert fin.payload["region_claim"] == {
        "text": "ภาคใต้", "text_norm": "ภาคใต้", "location": "title"
    }
    assert fin.payload["published_at"] == "2025-03-01"
    assert len(fin.content_hash) == 64


def test_the_record_has_nowhere_to_put_a_forbidden_field() -> None:
    names = {f.name for f in dataclasses.fields(ScrapedRecipe)}
    forbidden = {"method", "method_text", "instructions", "author", "username", "profile_url",
                 "comments", "photos", "image", "phone", "email", "address",
                 "register", "province", "province_label", "dish_category"}
    assert not names & forbidden


def test_published_at_is_never_invented() -> None:
    assert finalise(_rec(published_at=None)).payload["published_at"] is None


def test_thai_text_keeps_the_original_beside_the_normalised_form() -> None:
    title = "ประจ าปี แกงไตปลา"  # sara am broken as PDF extraction breaks it
    p = finalise(_rec(title_th=title, region_claim=None)).payload
    assert p["title_th"] == title, "original kept as found"
    assert p["title_th_norm"] == "ประจำปี แกงไตปลา"


def test_sara_am_is_repaired_in_the_normalised_twin_only() -> None:
    fin = finalise(_rec(site_tags=["จ าเป็น"]))
    assert fin.payload["site_tags"] == ["จ าเป็น"]
    assert fin.payload["site_tags_norm"] == ["จำเป็น"]


def test_personal_data_is_redacted_before_anything_is_returned() -> None:
    fin = finalise(_rec(
        title_th="แกงส้ม โดย นางสมหญิง ทดสอบ",
        region_claim=None,
        ingredient_lines=["ปลา 1 ตัว", "สั่งได้ที่ 081 234 5678", "ติดต่อ somchai@example.com"],
    ))
    assert not find_leaks(json.dumps(fin.payload, ensure_ascii=False))
    assert "สมหญิง" not in json.dumps(fin.payload, ensure_ascii=False)
    assert fin.redaction.total >= 3


@pytest.mark.parametrize(
    "kw,rule",
    [
        ({"ingredient_lines": ["ดูวิธีทำที่ https://new.example/u/cook"]}, "link"),
        ({"site_tags": ["photo_1234.jpg"]}, "image"),
        ({"ingredient_lines": ["ตั้งกระทะ " * 40]}, "prose"),
        ({"region_claim": Claim("ภาคเหนือ", "title")}, "rule 6"),
        ({"province_claim": Claim("สงขลา", "tag")}, "rule 6"),
        ({"region_claim": Claim("ภาคใต้", "somewhere")}, "unknown location"),  # type: ignore[arg-type]
        ({"scraped_at": datetime(2026, 10, 6)}, "timezone"),
        ({"url": "file:///etc/passwd"}, "http"),
    ],
)
def test_out_of_contract_records_are_refused(kw: dict[str, Any], rule: str) -> None:
    with pytest.raises(RecordRefused, match=rule):
        finalise(_rec(**kw))


def test_a_refusal_never_echoes_unredacted_claim_text() -> None:
    with pytest.raises(RecordRefused) as info:
        finalise(_rec(province_claim=Claim("นางสมหญิง ทดสอบ", "title")))
    assert "สมหญิง" not in str(info.value)


def test_claims_in_breadcrumb_or_intro_are_spans_not_passages() -> None:
    finalise(_rec(province_claim=Claim("ของดีเมืองสงขลา", "intro")))
    with pytest.raises(RecordRefused, match="prose"):
        finalise(_rec(province_claim=Claim("ก" * 300, "intro")))


class _Conn:
    def __init__(self) -> None:
        self.sql: list[str] = []

    def execute(self, sql: str, params: object = None) -> None:
        self.sql.append(sql)


def test_insert_writes_raw_recipes_and_nothing_else() -> None:
    conn = _Conn()
    insert_raw_recipe(conn, "newsite", finalise(_rec()), raw_path="data/raw/newsite/x.html",
                      http_status=200, fetched_at=NOW)
    assert len(conn.sql) == 1
    sql = conn.sql[0]
    assert "INSERT INTO raw_recipes" in sql
    for table in ("recipes ", "province_attribution", "dish_categor", "method_text"):
        assert table not in sql.replace("raw_recipes", "")


def test_insert_takes_only_finalised_output() -> None:
    with pytest.raises(TypeError):
        insert_raw_recipe(_Conn(), "newsite", {"url": "x"},  # type: ignore[arg-type]
                          raw_path="x", http_status=200, fetched_at=NOW)
    fin = finalise(_rec())
    fin.payload["method_text"] = "ตั้งกระทะ"
    with pytest.raises(RecordRefused):
        insert_raw_recipe(_Conn(), "newsite", fin, raw_path="x", http_status=200, fetched_at=NOW)
