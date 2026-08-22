"""PDPA redaction for the DCP forms — applied at parse time, before any write.

Rule 8 and ``ETHICS.md``: no personally identifying data enters the database, ever.
Not in a table, not in a JSONB blob, not in a log line. Filtering at export is too
late, because by then it is in the backups.

The DCP form carries contact detail in three places:

``§1.3 ชื่อผู้ให้ข้อมูล``
    The informant. Name, ``เลขที่`` (house number), ``หมู่``, ``ถนน`` (road),
    ``ตำบล/แขวง``, ``อำเภอ/เขต``, ``จังหวัด``, ``รหัสไปรษณีย์`` (postcode),
    ``หมายเลขโทรศัพท์`` (mobile).

``§1.4 ร้านอาหาร/แหล่ง``
    A business. The name is retained — a restaurant that asked to be publicised is not
    an informant — but its street address and phone are stripped.

Signature block
    ``ลงชื่อ ... ผู้เสนอเมนูอาหาร`` and the parenthesised name beneath it.

What is retained. Administrative geography only: ``จังหวัด`` (province) and
``อำเภอ/เขต`` (district). Administrative geography is not contact detail.

``ตำบล`` (subdistrict) is **dropped** pending HD-21. That gate is open; this module
implements its recommended option B so the parser has a definite contract, and the
choice is isolated in :data:`RETAIN_SUBDISTRICT` so reversing it is a one-line change
plus a re-parse. The 231 raw PDFs are retained on disk precisely so that re-parsing is
possible — see ``docs/decisions.md``.

Every removal is counted by class. A document yielding **zero** redactions is a parser
failure, not a clean document: these forms always carry contact fields, so zero means
the block was missed entirely.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# HD-21, option B (open — see docs/decisions.md). Flip to True and re-parse to retain.
RETAIN_SUBDISTRICT = False

REDACTED = "[REDACTED]"

# Honorific-initial compounds that are ROLES or royal styles, not personal names.
# These must be matched WHOLE. An earlier version stop-listed the bare syllables "ก"
# and "เอก" so that นายก ("mayor/premier") would survive — and thereby leaked นายกิตติ,
# นางสาวกนก and นายเอกชัย, which are ordinary given names beginning with those
# letters. Thai is unspaced, so only the full compound disambiguates.
#
# Where a compound is genuinely ambiguous the default is to REDACT. Losing a job title
# costs a little content; leaking a name is a compliance failure.
ROLE_COMPOUNDS = (
    "นายอำเภอ",
    "นางเธอ",
    "นายแพทย์",
    "นางพยาบาล",
    "นายช่าง",
    "นายทหาร",
    "นายกเทศมนตรี",
    "นายกองค์การ",
    "นายกรัฐมนตรี",
    "นายกสภา",
    "นายกอบต",
    "นายกเหล่ากาชาด",
)

# Thai and Arabic digits both appear, often mixed within one field. `_D` is the class
# *contents*, so it can be composed into larger classes; `_DIGIT` is the ready class.
# Writing _DIGIT inside another [...] builds a nested set, which silently matches only
# the first digit — that bug let a house number survive an early version of this module.
_D = r"0-9๐-๙"
_DIGIT = rf"[{_D}]"

# Horizontal whitespace only. Plain \s includes newlines, and a greedy run of it eats
# across a section boundary — an early version swallowed the "๑.๔" heading. Again the
# contents are kept separate from the class so they can be composed without nesting.
# The forms use NBSP and thin spaces as well as plain spaces.
_WS = " \t\xa0\u1680\u2000-\u200a\u202f\u205f\u3000"
_H = rf"[{_WS}]"

# Honorifics that anchor a personal name. Deliberately excludes พระ and คุณ: Thai is
# unspaced, so พระ matches inside นครพระชุม and คุณ inside สรรพคุณ (the ingredient
# table's own column header). Both produced false positives on real documents.
_HONORIFIC = r"(?:นางสาว|นาง|นาย|น\.ส\.|ด\.ช\.|ด\.ญ\.)"
# Must not be preceded by a Thai letter, or it is part of a longer word.
_H_ANCHORED = rf"(?<![ก-๎]){_HONORIFIC}"

PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    # (class, description, pattern) — `class` maps to a redaction_log column.
    (
        "phone",
        "telephone / mobile after its label",
        re.compile(rf"(หมายเลขโทรศัพท์){_H}*[:：]?{_H}*{_DIGIT}[{_D}{_WS}\-]{{6,}}"),
    ),
    (
        "phone",
        "bare 9-10 digit number",
        re.compile(rf"(?<![{_D}])0{_DIGIT}[{_WS}\-]?{_DIGIT}{{3,4}}[{_WS}\-]?{_DIGIT}{{4}}(?![{_D}])"),
    ),
    (
        "email",
        "email address",
        re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    ),
    (
        "name",
        "informant name after the §1.3 label",
        re.compile(rf"(ชื่อผู้ให้ข้อมูล){_H}*[^\n]{{0,60}}"),
    ),
    (
        "name",
        "signature line",
        re.compile(r"(ลงชื่อ)[^\n]{0,80}?ผู้เสนอ"),
    ),
    (
        "name",
        "parenthesised name with honorific",
        re.compile(rf"\({_H}*{_HONORIFIC}[^)\n]{{0,50}}\)"),
    ),
    (
        "name",
        "any honorific followed by a personal name, anywhere in the document",
        # Label-anchored stripping is not sufficient: a corpus scan found 168 names in
        # 117 documents outside the §1.3 and signature blocks — in §2 prose, in
        # ตำแหน่ง lines, and in layouts using a different label. ROLE_AFTER_HONORIFIC
        # keeps titles (นายอำเภอ = district chief) and royal forms out of the match.
        re.compile(rf"{_H_ANCHORED}{_H}*[ก-๙]{{2,}}(?:{_H}+[ก-๙]{{2,}})?"),
    ),
    (
        "address",
        "house number",
        re.compile(rf"(เลขที่){_H}*[:：]?{_H}*{_DIGIT}[{_D}/\-]*"),
    ),
    (
        "address",
        "moo (village number)",
        re.compile(rf"(หมู่(?:ที่)?){_H}*[:：]?{_H}*{_DIGIT}{{1,3}}"),
    ),
    (
        "address",
        "road name",
        re.compile(rf"(ถนน){_H}*[:：]?{_H}*[^\s\n]{{1,40}}"),
    ),
    (
        "address",
        "postcode",
        re.compile(rf"(รหัสไปรษณีย์){_H}*[:：]?{_H}*{_DIGIT}{{5}}"),
    ),
    (
        "coordinates",
        "lat/long pair",
        re.compile(r"\b\d{1,2}\.\d{4,}\s*,\s*\d{2,3}\.\d{4,}\b"),
    ),
    (
        "media_link",
        "URL",
        re.compile(r"https?://\S+"),
    ),
]

if not RETAIN_SUBDISTRICT:
    PATTERNS.append(
        (
            "address",
            "subdistrict (HD-21 option B)",
            re.compile(
                rf"(ตำบล){_H}*/?{_H}*(?:แขวง)?"
                rf"{_H}*[:：]?{_H}*[^\s\n]{{1,30}}"
            ),
        )
    )


@dataclass
class RedactionReport:
    """Per-class counts, shaped to the `redaction_log` columns."""

    n_names: int = 0
    n_addresses: int = 0
    n_phone_numbers: int = 0
    n_emails: int = 0
    n_coordinates: int = 0
    n_media_links: int = 0

    @property
    def total(self) -> int:
        return (
            self.n_names
            + self.n_addresses
            + self.n_phone_numbers
            + self.n_emails
            + self.n_coordinates
            + self.n_media_links
        )

    @property
    def suspected_parser_failure(self) -> bool:
        """Zero redactions means the contact block was missed, not that it was absent."""
        return self.total == 0

    #: redaction class -> the redaction_log column it counts toward
    COLUMNS = {
        "name": "n_names",
        "address": "n_addresses",
        "phone": "n_phone_numbers",
        "email": "n_emails",
        "coordinates": "n_coordinates",
        "media_link": "n_media_links",
    }

    def _bump(self, cls: str) -> None:
        column = self.COLUMNS[cls]
        setattr(self, column, getattr(self, column) + 1)


def _is_role_not_name(matched: str) -> bool:
    """True when an honorific match is a title or royal style, not a personal name."""
    return matched.startswith(ROLE_COMPOUNDS)


def redact(text: str) -> tuple[str, RedactionReport]:
    """Strip every personal-data class from `text`. Call before anything is stored.

    Field *labels* survive; their values do not. Keeping ``หมายเลขโทรศัพท์
    [REDACTED]`` rather than deleting the line makes it visible in a spot check that
    redaction ran, instead of leaving a gap that looks like the form was blank.
    """
    report = RedactionReport()

    for cls, _desc, pattern in PATTERNS:
        def _sub(m: re.Match[str], _c: str = cls, _p: re.Pattern[str] = pattern) -> str:
            if _c == "name" and _is_role_not_name(m.group(0)):
                return m.group(0)
            report._bump(_c)
            # Preserve a leading label group so the redaction is legible.
            if m.groups() and m.group(1):
                return f"{m.group(1)} {REDACTED}"
            return REDACTED

        text = pattern.sub(_sub, text)

    return text, report


# Detection patterns used by tests/test_pdpa.py to assert nothing survived into a
# table. Deliberately BROADER than the redaction patterns above: a leak that the
# stripper missed should still be caught here.
LEAK_PATTERNS: dict[str, re.Pattern[str]] = {
    "phone": re.compile(
        rf"(?<![{_D}])0{_DIGIT}[{_WS}\-]?{_DIGIT}{{3,4}}[{_WS}\-]?{_DIGIT}{{4}}(?![{_D}])"
    ),
    "email": re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    "honorific_name": re.compile(rf"{_H_ANCHORED}{_H}*[ก-๎]{{2,}}"),
    "house_number": re.compile(rf"เลขที่{_H}*{_DIGIT}"),
    "postcode": re.compile(rf"รหัสไปรษณีย์{_H}*{_DIGIT}{{5}}"),
    "road": re.compile(rf"ถนน{_H}*[ก-๎A-Za-z]{{2,}}"),
}


def find_leaks(text: str) -> dict[str, list[str]]:
    """Any personal-data-shaped substring in `text`. Empty dict means clean."""
    if not text:
        return {}
    out: dict[str, list[str]] = {}
    for name, pattern in LEAK_PATTERNS.items():
        hits = [m.group(0) for m in pattern.finditer(text)]
        if name == "honorific_name":
            hits = [h for h in hits if not _is_role_not_name(h)]
        if hits:
            out[name] = hits
    return out
