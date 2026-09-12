"""PDPA: `source_info_th` (Task 3e) is redacted before it would ever be written.

`source_info_th` is free-text source attribution from a government publication — the
same shape of field the DCP forms carry contact detail in (`src/ingest/pdpa.py`'s
module docstring: informant name, address, phone). `scripts/parse_food67.py` runs it
through that same shared stripper rather than a new one; these tests exercise that
choice directly against the stripper, since the loader itself cannot run without the
real CSV (see `docs/decisions.md`).

PII fixtures are invented, in the `ทดสอบ` ("test") convention `tests/test_pdpa.py`
already uses — never from a real file, which this project does not have a copy of.
"""

from __future__ import annotations

from src.ingest.pdpa import find_leaks, redact


def test_source_info_with_name_and_phone_is_redacted() -> None:
    text = "เรียบเรียงโดย นางสมหญิง ทดสอบ โทร 08 1234 5678"
    clean, report = redact(text)
    assert report.total > 0
    assert not find_leaks(clean)
    assert "สมหญิง" not in clean
    assert "ทดสอบ" not in clean or "[REDACTED]" in clean


def test_source_info_with_only_a_publication_citation_is_unaffected() -> None:
    """The common, non-PII case: a citation naming a department or publication, not
    a person. Nothing to redact, and nothing should be removed."""
    text = "กรมส่งเสริมวัฒนธรรม กระทรวงวัฒนธรรม, หนังสือ 1 จังหวัด 1 เมนู เชิดชูอาหารถิ่น ประจำปี 2567"
    clean, report = redact(text)
    assert clean == text
    assert report.total == 0


def test_source_info_empty_field_round_trips_clean() -> None:
    clean, report = redact("")
    assert clean == ""
    assert report.total == 0


def test_source_info_with_address_is_redacted() -> None:
    text = "ติดต่อได้ที่ เลขที่ 99/9 หมู่ 6 ถนน ทดสอบ"
    clean, report = redact(text)
    assert report.total > 0
    assert not find_leaks(clean)
    assert "99/9" not in clean
