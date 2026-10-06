"""PDPA: no personal data survives into any table, or into any parsed record.

`ETHICS.md` states the rule; this file is what makes it true rather than aspirational.
It runs at three levels:

1. **Unit** — the stripper removes each class from synthetic text.
2. **Corpus** — every real document redacts clean, and the role/name boundary that
   caused a real leak stays fixed.
3. **Database** — every text column of every table is scanned for personal-data shapes.

The database test is the one that matters: it does not trust the parser, it inspects
what actually landed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config import RAW_DIR
from src.db import get_connection
from src.ingest.pdf_layout import read_document
from src.ingest.pdpa import find_leaks, redact, scan_database

RAW = RAW_DIR / "dcp_food"

# Fixtures below are INVENTED, never lifted from the corpus. An earlier draft of this
# file used a real informant's name, mobile number and house number copied out of
# north_1_1.pdf — which would have published exactly the data this module exists to
# strip, in the file that claims to enforce the rule. Surname ทดสอบ ("test") marks
# every personal-data fixture as synthetic.


# ── 1. unit ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "text",
    [
        "ชื่อผู้ให้ข้อมูล นางสมหญิง ทดสอบ",
        "หมายเลขโทรศัพท์ 08 1234 5678",
        "เลขที่ ๙๙/๙ หมู่ ๖",
        "รหัสไปรษณีย์ ๑๐๑๐๐",
        "ถนน ทดสอบ",
        "somchai@example.com",
        "(นางสมหญิง ทดสอบ)",
    ],
)
def test_each_class_is_stripped(text: str) -> None:
    clean, report = redact(text)
    assert report.total > 0, f"nothing redacted from {text!r}"
    assert not find_leaks(clean), f"leak survived: {find_leaks(clean)}"


@pytest.mark.parametrize("text", ["ทดสอบ@example.com", "ติดต่อ สมหญิง.ทดสอบ@example.co.th"])
def test_an_email_with_a_thai_local_part_is_detected(text: str) -> None:
    """Regression, 2026-09-29: the leak pattern accepted only ASCII before the @, so an
    internationalised address passed every refusal and database scan."""
    assert "email" in find_leaks(text)


def test_an_at_sign_in_ordinary_text_is_not_an_email() -> None:
    assert "email" not in find_leaks("ราคา 50 บาท @ ร้านข้างตลาด")


def test_administrative_geography_is_retained() -> None:
    """District and province are not contact detail and must survive."""
    clean, _ = redact("อำเภอ/เขต เมืองกำแพงเพชร จังหวัด กำแพงเพชร")
    assert "เมืองกำแพงเพชร" in clean
    assert "กำแพงเพชร" in clean


def test_subdistrict_is_dropped_per_hd21() -> None:
    clean, _ = redact("ตำบล/แขวง นครชุม อำเภอ/เขต เมือง")
    assert "นครชุม" not in clean
    assert "เมือง" in clean


@pytest.mark.parametrize(
    "role", ["นายอำเภอลี้", "นางเธอในพระบาทสมเด็จ", "นายกองค์การบริหารส่วนตำบล"]
)
def test_roles_are_not_mistaken_for_names(role: str) -> None:
    """นายอำเภอ is a district chief, not an informant. Redacting it destroys content."""
    clean, _ = redact(role)
    assert clean == role


@pytest.mark.parametrize("name", ["นายกิตติ", "นางสาวกนก", "นายเอกชัย", "นางกัลยา"])
def test_names_beginning_with_role_syllables_are_still_stripped(name: str) -> None:
    """Regression: a prefix-based role stop-list leaked every name starting with ก or เอก."""
    clean, report = redact(name)
    assert report.n_names > 0, f"{name} was treated as a role"
    assert name not in clean


# ── 2. corpus ─────────────────────────────────────────────────────────────────

def _pdfs() -> list[Path]:
    return sorted(RAW.glob("*.pdf"))


@pytest.mark.skipif(not RAW.exists(), reason="raw corpus not present")
def test_no_document_leaks_after_redaction() -> None:
    offenders: dict[str, dict[str, list[str]]] = {}
    for path in _pdfs():
        clean, _ = redact(read_document(path).raw_text)
        if leaks := find_leaks(clean):
            offenders[path.name] = leaks
    assert not offenders, (
        f"personal data survived redaction in {len(offenders)} documents: {offenders}"
    )


# ── 3. database ───────────────────────────────────────────────────────────────



def test_no_personal_data_in_any_table() -> None:
    """Scan every text and JSON column of every project table.

    JSONB is included deliberately: `raw_recipes.parsed_json` holds the parser's own
    output, and "not in a table, not in a JSONB blob" is the rule as ETHICS.md states
    it. Trusts nothing upstream: it inspects what actually landed. The scan itself is
    `src.ingest.pdpa.scan_database`, the same one every scraper load runs.
    """
    conn = get_connection()
    try:
        assert conn.execute(
            "SELECT count(*) FROM information_schema.columns WHERE table_schema = 'public'"
        ).fetchone()[0], "no project columns found: schema not migrated?"
        offenders = scan_database(conn)
    finally:
        conn.close()
    assert not offenders, "personal data found in the database: " + "; ".join(offenders[:20])


def test_khun_does_not_block_the_honorific_behind_it() -> None:
    """`คุณ` is excluded from the honorific set because it matches inside สรรพคุณ and
    คุณภาพ — but excluding it also let the anchor treat it as an ordinary preceding
    letter, so `โดย คุณนางสาว…` survived redaction on a kapook contributor credit."""
    out, report = redact("โดย คุณนางสาวเซา")
    assert "เซา" not in out
    assert report.n_names == 1


def test_a_contributor_handle_is_a_name() -> None:
    """Web sources credit by handle, not by name. Latin script after คุณ is the
    discriminator: no ordinary Thai word puts it there."""
    out, report = redact("สูตรจาก คุณ tukata001 นะคะ")
    assert "tukata001" not in out
    assert report.n_names == 1


def test_the_khun_rules_do_not_fire_on_ordinary_thai_words() -> None:
    """สรรพคุณ is the DCP ingredient table's own column header. คุณภาพ, คุณค่า and คุณแม่
    are unavoidable in recipe prose. Any of them redacting would gut the corpus."""
    for phrase in ("สรรพคุณของขิง", "อาหารมีคุณภาพดี", "คุณแม่ทำให้กิน", "เครื่องปรุงคุณค่าสูง"):
        out, report = redact(phrase)
        assert out == phrase and report.n_names == 0
