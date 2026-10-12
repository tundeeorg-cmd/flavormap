"""scripts/inventory_sources.py (T1.13a): personal data is counted, never shown. All
values are synthetic (surname ทดสอบ, invented numbers)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.inventory_sources import LINE_ID, SPECS, leak_counts, section


def test_leaks_are_counted_per_class_per_row() -> None:
    frame = pd.DataFrame({
        "a": ["แกงทดสอบ", "โทร 081-234-5678", "ไลน์: ทดสอบ"],
        "b": ["", "ติดต่อ ทดสอบ@example.com", None],
    })
    counts = leak_counts(frame)
    assert counts["phone"] == 1 and counts["email"] == 1 and counts["line_id"] == 1


def test_an_email_address_is_not_a_line_handle() -> None:
    assert not LINE_ID.search("ทดสอบ@example.com")
    assert LINE_ID.search("แอดไลน์ @flavortest")


def test_the_report_never_contains_a_personal_value(tmp_path: Path) -> None:
    spec = next(s for s in SPECS if s.slug == "tat_food")
    folder = tmp_path / "tat_food"
    folder.mkdir()
    pd.DataFrame({
        "source_url": ["u1", "u2", "u3"],
        "dish_th": ["แกงทดสอบ", "นางสมหญิง ทดสอบ", "ข้าวทดสอบ"],
        "province_th": ["เชียงราย", "น่าน", "น่าน"],
        "page_date": ["2026-01-01"] * 3,
        "list_kind": ["campaign"] * 3,
        "region": ["North"] * 3,
        "ingredients_listed": ["ข่า", "", "โทร 089-876-5432"],
        "captured_on": ["2026-10-06"] * 3,
    }).to_csv(folder / spec.table, index=False)
    report = "\n".join(section(spec, folder))
    assert "สมหญิง" not in report and "089" not in report
    assert "phone 1" in report and "honorific_name 1" in report
    assert "แกงทดสอบ (เชียงราย)" in report and "ข้าวทดสอบ (น่าน)" in report
