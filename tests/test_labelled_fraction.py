"""A bare substring search for a Thai province name is a homograph count, not a label.

Thai is unspaced, so there is no word boundary to anchor on. `เลย` is Loei province and
also the adverb "at all"; it appears in 2,384 of the 2,702 cached kapook pages,
overwhelmingly inside `คลิกเลย` ("click here"). Matching it bare puts the labelled
fraction at 94.9%. Requiring a `จังหวัด` marker for the ambiguous names puts it at 3.5%,
and hand-reading those puts it at 1.3% — see `docs/labelled_fraction.md`.

These tests pin the rules apart, because the difference between them is two orders of
magnitude and a silent change to the ambiguous set would move the project's headline
number without moving a test.
"""

from __future__ import annotations

from scripts.measure_labelled_fraction import (
    AMBIGUOUS,
    RULES,
    load_provinces,
    province_hits,
    region_hits,
)

PROVINCES = load_provinces()
LOEI = "TH-42"
CHIANG_MAI = "TH-50"
BANGKOK = "TH-10"


def hits(text: str, rule: str) -> set[str]:
    return province_hits(text, PROVINCES, rule)


def test_the_click_here_link_is_not_loei_province() -> None:
    """`คลิกเลย` is the single largest source of false province labels in the corpus."""
    text = "สูตรอาหาร เมนูอาหารแบบง่ายๆ เคล็ดลับการทำอาหาร คลิกเลย"
    assert hits(text, "permissive") == {LOEI}
    assert hits(text, "strict") == set()
    assert hits(text, "marker") == set()


def test_sun_drying_is_not_tak_province() -> None:
    """`ตาก` is a cooking verb before it is a province — 324 occurrences, ตากแดด."""
    assert hits("นำออกไปตากแดดจนเนื้อหมาด", "permissive") == {"TH-63"}
    assert hits("นำออกไปตากแดดจนเนื้อหมาด", "strict") == set()


def test_an_ambiguous_name_still_counts_when_it_is_marked() -> None:
    """The rule drops the homograph, not the province. Loei with a จังหวัด in front of it
    is a claim, and dropping it would be as wrong as counting คลิกเลย."""
    assert hits("แจ่วบองสูตรจังหวัดเลย", "strict") == {LOEI}
    assert hits("แจ่วบองสูตรจังหวัดเลย", "marker") == {LOEI}


def test_an_unambiguous_name_needs_no_marker_except_under_the_floor_rule() -> None:
    assert hits("น้ำพริกหนุ่มแบบเชียงใหม่", "strict") == {CHIANG_MAI}
    assert hits("น้ำพริกหนุ่มแบบเชียงใหม่", "marker") == set()
    assert hits("น้ำพริกหนุ่ม จังหวัดเชียงใหม่", "marker") == {CHIANG_MAI}


def test_bangkok_is_unmatchable_without_its_running_form() -> None:
    """Nobody writes กรุงเทพมหานคร in a recipe. Without the alias the capital scores zero
    and the omission would look like a finding about Bangkok rather than about spelling."""
    assert hits("ร้านหมูกระทะน่าหม่ำในกรุงเทพฯ", "strict") == {BANGKOK}
    assert hits("ผัดหมี่โคราช", "strict") == {"TH-30"}


def test_every_ambiguous_name_is_a_real_province() -> None:
    """A typo in the ambiguous set would silently exempt nothing and re-admit a homograph."""
    names = {p.name_th for p in PROVINCES}
    assert set(AMBIGUOUS) <= names


def test_the_rules_are_ordered_from_loosest_to_tightest() -> None:
    """Each rule must be a subset of the one before it, on any text. If `strict` could
    admit something `permissive` does not, the three columns would not be comparable."""
    text = "แจ่วบองจังหวัดเลย กับน้ำพริกหนุ่มเชียงใหม่ ตากแดดไว้ คลิกเลย"
    found = [hits(text, rule) for rule in RULES]
    assert found[0] >= found[1] >= found[2]
    assert found[0] == {LOEI, CHIANG_MAI, "TH-63"}
    assert found[1] == {LOEI, CHIANG_MAI}
    assert found[2] == {LOEI}


def test_a_bare_direction_word_is_not_a_region_claim() -> None:
    """`เหนือ` is "above" and `ใต้` is "below". Only the compounded forms are about food."""
    assert region_hits("วางกระทะเหนือเตา แล้ววางฝาไว้ใต้จาน") == set()
    assert region_hits("อาหารพื้นบ้านล้านนา รสเด็ดแบบปักษ์ใต้") == {"North", "South"}
    assert region_hits("รวมสูตรส้มตำและอาหารอีสาน") == {"Northeast"}
