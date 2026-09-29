"""scripts/verify_checkboxes.py: the per-record report for checking checkbox extraction
by eye. It must report every document in a province's group, including one the loader
skipped, and never assert or summarise on the reader's behalf."""

from __future__ import annotations

import pytest

from scripts.verify_checkboxes import report
from src.config import RAW_DIR
from src.ingest.pdpa import find_leaks

pytestmark = pytest.mark.skipif(
    not (RAW_DIR / "dcp_food").exists(), reason="raw DCP corpus not present"
)


def test_reports_each_document_including_one_the_loader_skipped() -> None:
    text = report(["นครราชสีมา", "บุรีรัมย์"])
    for doc in ("northeast_5_1", "northeast_5_2", "northeast_5_3",
                "northeast_6_1", "northeast_6_2", "northeast_6_3"):
        assert f"{doc}.pdf   (group of" in text
    assert "NO recipes row" in text  # northeast_5_3: province field failed to parse


def test_every_box_is_listed_with_page_and_coordinates() -> None:
    text = report(["บุรีรัมย์"])
    block = text.split("northeast_6_3.pdf")[-1]  # after the PDF path line
    assert "TICKED  p.3  x= 106.9  y= 709.3  U+F0FE" in block  # the near_lost box
    assert block.count("empty ") > 0  # unticked boxes are shown too


def test_output_carries_no_personal_data() -> None:
    assert not find_leaks(report(["นครราชสีมา", "บุรีรัมย์"]))


def test_a_province_with_no_documents_is_said_plainly() -> None:
    assert "No attributed documents found for: ไม่มีจังหวัดนี้" in report(["ไม่มีจังหวัดนี้"])
