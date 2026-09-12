"""GI (geographical-indication) product safety classification — Task 4b of the
`datago_catalog` brief.

**The brief's own filter is too narrow, confirmed against real data.** Task 4b names
two exact phrases as the registrant-list signature: "ผู้ขอใช้" and "ผู้ผลิตที่ใช้".
Against the real 61 distinct GI-classified dataset titles found across both
catalogues, matching only those two phrases catches 6 — but titles like
"ผู้ประกอบการที่ขอใช้ตราสัญลักษณ์..." (business operators who applied...),
"เกษตรกรที่ได้รับการขึ้นทะเบียน..." (farmers registered...), "ผู้ปลูก...ที่ขอใช้
ตรา..." (growers who applied...), and "รายชื่อผู้ที่ได้รับหนังสืออนุญาต..." (the
LIST of those granted a licence...) are the same shape of hazard — a list of named
individuals or businesses — under different phrasing. :func:`is_registrant_level`
catches this wider set.

**Deliberately conservative, and deliberately not the last word.** Rule 8 makes a
false negative (calling a registrant list "safe") far more costly than a false
positive (holding back a genuinely safe product-level dataset for review) — so this
function defaults to *registrant-level* whenever a title names "who" rather than "how
many"/"how much": an aggregate marker (จำนวน "count of", มูลค่า "value of", ราคา
"price of", สถิติ "statistics", ปริมาณ "quantity of", ร้อยละ "percentage of", พื้นที่
"area of", ผลผลิต "yield of", ช่องทาง "channel of") overrides a registrant marker,
because "จำนวนผู้ได้รับอนุญาต..." ("the NUMBER who were permitted...") is a count, not
a list, and carries no more personal data than the number itself. Nothing here is a
green light to auto-harvest: every dataset this module calls safe still needs a human
to look at the actual resource before it is fetched, per the brief's own "do not
bulk-fetch beyond this shortlist without review."
"""

from __future__ import annotations

from dataclasses import dataclass

#: Any of these appearing anywhere in a title makes it read as "a list of who",
#: not exhaustive — a title using none of these can still be registrant-level and
#: this function will miss it, which is exactly why nothing here is a green light on
#: its own.
REGISTRANT_MARKERS: tuple[str, ...] = (
    "รายชื่อ",       # "list of [names]"
    "ผู้ขอใช้",       # the brief's own first example
    "ผู้ผลิตที่ใช้",   # the brief's own second example
    "ผู้ประกอบการที่",
    "ผู้ปลูก",
    "ผู้ได้รับ",
    "ผู้เลี้ยง",
    "เกษตรกรที่",
    "เกษตรกรผู้",
)

#: Any of these overrides a registrant marker — the title is naming a count, value,
#: or area, not a person.
AGGREGATE_MARKERS: tuple[str, ...] = (
    "จำนวน", "มูลค่า", "ราคา", "สถิติ", "ปริมาณ", "ร้อยละ", "พื้นที่", "ผลผลิต", "ช่องทาง",
)


def is_registrant_level(dataset_title_th: str) -> bool:
    """True if `dataset_title_th` reads as a list of named individuals/businesses
    (never to be harvested, per Bible §4 and Task 4b) rather than a product
    designation or an aggregate statistic about one."""
    title = dataset_title_th or ""
    if any(m in title for m in AGGREGATE_MARKERS):
        return False
    return any(m in title for m in REGISTRANT_MARKERS)


@dataclass
class GiCandidate:
    dataset_title_th: str
    province_th: str
    resource_url: str
    registrant_level: bool
    # A best-effort product name extracted from the title, for the product_name_th
    # column a human confirms before it goes into gi_products — never inserted
    # automatically by this module.
    likely_product_name: str | None


def extract_likely_product_name(dataset_title_th: str) -> str | None:
    """A rough guess at the product name embedded in a GI dataset title — e.g.
    "ข้าวหอมมะลิสุรินทร์" out of "ผู้ขอใช้ตราสิ่งบ่งชี้ทางภูมิศาสตร์ข้าวหอมมะลิสุรินทร์".
    Strips the common GI boilerplate prefixes; returns the remainder if anything is
    left, else None. A starting point for human review, not a parser to be trusted
    as-is — `gi_products.product_name_th` is filled in by a human, not by this.
    """
    title = dataset_title_th or ""
    prefixes = (
        "ผู้ขอใช้ตราสิ่งบ่งชี้ทางภูมิศาสตร์",
        "ผู้ผลิตที่ใช้ตราสิ่งบ่งชี้ทางภูมิศาสตร์",
        "ตราสิ่งบ่งชี้ทางภูมิศาสตร์",
        "ตราสัญลักษณ์สิ่งบ่งชี้ทางภูมิศาสตร์",
        "สิ่งบ่งชี้ทางภูมิศาสตร์",
    )
    for p in prefixes:
        if title.startswith(p):
            remainder = title[len(p) :].strip()
            return remainder or None
    return None
