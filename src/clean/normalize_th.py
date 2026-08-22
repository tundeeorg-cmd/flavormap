"""Repair Thai text damaged by PDF extraction.

Two defects appear in the DCP corpus (measured in `docs/extractor_comparison.md`):

1. **Orphaned combining marks** — ``หมู่`` → ``หม ู่``, ``ที่`` → ``ท ี่``. A Thai vowel
   or tone mark is separated from its base consonant by whitespace.
2. **Broken sara am** — ``ประจำปี`` → ``ประจ าปี``. The ``ำ`` is dropped and replaced by
   a space, leaving a bare ``า``.

The obvious fix — strip spaces before Thai vowels — is wrong, and the project brief says
so. Thai does not put spaces between words, so a space is usually a phrase boundary; a
blanket regex would silently weld unrelated words together and the damage would be
invisible until ingredient tokens stopped matching the lexicon.

What this module does instead:

* **Defect 1 is unambiguous.** A Thai combining mark can never legitimately follow
  whitespace — there is nothing for it to combine with. Joining is always correct.
* **Defect 2 is ambiguous** and is resolved by segmentation, not by lookup. At each site
  both repairs are tried — join as ``า``, or substitute ``ำ`` — and each candidate run is
  segmented with PyThaiNLP ``newmm`` and scored ``(unknown tokens, total tokens)``. The
  lower score wins.

  Looking the run up in the dictionary directly does not work, because a Thai run is a
  phrase rather than a word: ``ประจำปีงบประมาณ`` is no more a dictionary entry than
  ``ประจาปีงบประมาณ`` is. Nor is an unknown-token count sufficient on its own — ``ประ``
  and ``จา`` are both genuine words, so the wrong reading can segment into entirely known
  tokens. It is the *number* of tokens that separates them.

  ``น้ า`` is deliberately left unrepaired: ``น้ำ`` (water) and ``น้า`` (aunt/uncle) score
  identically, and in a recipe corpus guessing "water" would be right often enough to be
  dangerous. Unresolved sites are counted, so the residue stays visible rather than being
  assumed away.

Everything is NFC-normalised first, so composed and decomposed forms compare equal.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

# Thai combining marks: above/below vowels, tone marks, thanthakhat, nikhahit.
COMBINING_MARKS = "ัิีึืฺุู็่้๊๋์ํ๎"
SARA_AA = "า"   # า
SARA_AM = "ำ"   # ำ
THAI_CONSONANTS = "ก-ฮ"
THAI_RUN = re.compile(r"[฀-๿]+")

# ── Defect 3: private-use tone marks ─────────────────────────────────────────
# Some Thai fonts in the DCP corpus encode combining marks in the U+F700 private-use
# block instead of the Thai block, so extraction yields ``ด้าน`` as ``ดาน``.
# 14 of 231 documents are affected, 3,930 occurrences.
#
# Each entry below was verified against its own context in the corpus rather than
# taken from a published table:
#
#   U+F70B  ด?าน → ด้าน, ท?อง → ท้อง, พร?าว → พร้าว
#   U+F70A  แหล?ง → แหล่ง, ส?ง → ส่ง, ต?อ → ต่อ
#   U+F712  เป?น → เป็น
#   U+F70E  ณีย? → ณีย์, ลักษณ? → ลักษณ์
#   U+F710  ป?ญญา → ปัญญา
#   U+F706  ฟ?า → ฟ้า, ป?าย → ป้าย
#   U+F701  กะป? → กะปิ
#   U+F702  จำป?งบ → จำปีงบ, เป?ยก → เปียก
#
# These eight cover 3,912 of 3,930 occurrences. U+F705 (12) and U+F70C (6) are left
# unmapped: too few instances to verify, and a wrong mark is worse than a visible one.
PUA_MARKS = {
    "\uf701": "\u0e34",  # ิ
    "\uf702": "\u0e35",  # ี
    "\uf706": "\u0e49",  # ้
    "\uf70a": "\u0e48",  # ่
    "\uf70b": "\u0e49",  # ้
    "\uf70e": "\u0e4c",  # ์
    "\uf710": "\u0e31",  # ั
    "\uf712": "\u0e47",  # ็
}
_PUA_TABLE = str.maketrans(PUA_MARKS)
_PUA_RESIDUE = re.compile(r"[\uf700-\uf71f]")


def repair_pua(text: str) -> tuple[str, int, int]:
    """Map private-use Thai marks to their Thai-block equivalents.

    Returns (repaired, n_mapped, n_unmapped). Unmapped PUA codepoints are left in
    place so they stay visible downstream rather than silently becoming wrong text.
    """
    if not text:
        return text, 0, 0
    mapped = sum(text.count(c) for c in PUA_MARKS)
    out = text.translate(_PUA_TABLE)
    return out, mapped, len(_PUA_RESIDUE.findall(out))

# A combining mark preceded by whitespace — defect 1. The character before the gap may
# itself be a combining mark: `ท่ ี` stacks a tone mark and a vowel on one consonant and
# the extractor can split between them.
_ORPHAN = re.compile(f"(?<=[{THAI_CONSONANTS}{SARA_AA}{COMBINING_MARKS}])\\s+([{COMBINING_MARKS}])")
# A consonant, whitespace, then sara aa — defect 2.
_BROKEN_AM = re.compile(f"([{THAI_CONSONANTS}][{COMBINING_MARKS}]*)\\s+({SARA_AA})")


@dataclass
class NormalizationReport:
    pua_marks_mapped: int = 0
    pua_marks_unmapped: int = 0
    orphan_marks_joined: int = 0
    sara_am_repaired: int = 0
    sara_am_joined_as_aa: int = 0
    sara_am_ambiguous: int = 0
    ambiguous_samples: list[str] | None = None

    @property
    def total_repairs(self) -> int:
        return self.orphan_marks_joined + self.sara_am_repaired + self.sara_am_joined_as_aa


@lru_cache(maxsize=1)
def _dictionary() -> frozenset[str]:
    from pythainlp.corpus import thai_words
    return frozenset(thai_words())


def _thai_run_around(text: str, index: int) -> tuple[int, int]:
    """Bounds of the maximal Thai run containing `index`.

    Note this is a *run*, not a word. Thai does not space between words, so a run is
    typically a whole phrase — which is why the arbitration below segments it rather
    than looking it up whole.
    """
    start = index
    while start > 0 and "฀" <= text[start - 1] <= "๿":
        start -= 1
    end = index
    while end < len(text) and "฀" <= text[end] <= "๿":
        end += 1
    return start, end


def _segmentation_cost(run: str) -> tuple[int, int]:
    """Score a candidate reading: (unknown tokens, total tokens). Lower is better.

    Neither candidate is a dictionary entry on its own — Thai runs are phrases, not
    words — so the arbitration segments each reading and compares the results.

    Two signals, in priority order:

    * **Unknown tokens.** `ตาบล` leaves a stray `ล` behind; `ตำบล` is one clean word.
    * **Token count.** Where both readings segment into known words, the correct one
      still yields fewer, longer tokens — `ประจำ|ปีงบประมาณ` (2) against
      `ประ|จา|ปีงบประมาณ` (3), and `จำเป็น` (1) against `จา|เป็น` (2). `ประ` and `จา`
      are both genuine words, so an unknown-token count alone cannot separate them.
      This is maximal matching's usual assumption and it is doing real work here.

    A tie on both leaves the site unrepaired, which is how `น้ า` stays ambiguous:
    `น้ำ` and `น้า` are each a single known token.
    """
    from pythainlp.tokenize import word_tokenize

    words = _dictionary()
    tokens = [t for t in word_tokenize(run, engine="newmm") if t.strip()]
    unknown = sum(1 for t in tokens if t not in words)
    return unknown, len(tokens)


def normalize_thai(text: str, collect_samples: bool = False) -> tuple[str, NormalizationReport]:
    """Return repaired text and a report of what was changed."""
    report = NormalizationReport(ambiguous_samples=[] if collect_samples else None)
    if not text:
        return text, report

    # Defect 3 first: PUA marks must become real Thai marks before the orphan and
    # sara-am passes can recognise them as combining characters at all.
    text, report.pua_marks_mapped, report.pua_marks_unmapped = repair_pua(text)

    text = unicodedata.normalize("NFC", text)

    # ── Defect 1: orphaned combining marks. Always safe. ──────────────────────
    text, n = _ORPHAN.subn(r"\1", text)
    report.orphan_marks_joined = n

    # ── Defect 2: broken sara am. Segmentation-arbitrated, one site at a time. ──
    out: list[str] = []
    cursor = 0
    for match in _BROKEN_AM.finditer(text):
        base = match.group(1)

        joined = text[: match.start()] + base + SARA_AA + text[match.end():]
        substituted = text[: match.start()] + base + SARA_AM + text[match.end():]
        pivot = match.start() + len(base)

        s1, e1 = _thai_run_around(joined, pivot)
        s2, e2 = _thai_run_around(substituted, pivot)
        cand_aa, cand_am = joined[s1:e1], substituted[s2:e2]

        # Lower segmentation cost is the better reading.
        cost_aa = _segmentation_cost(cand_aa)
        cost_am = _segmentation_cost(cand_am)

        if cost_am < cost_aa:
            replacement = base + SARA_AM
            report.sara_am_repaired += 1
        elif cost_aa < cost_am:
            replacement = base + SARA_AA
            report.sara_am_joined_as_aa += 1
        else:
            # Both readings valid, or neither. Leave the text exactly as found —
            # an unrepaired defect is visible downstream; a wrong repair is not.
            replacement = match.group(0)
            report.sara_am_ambiguous += 1
            if collect_samples and report.ambiguous_samples is not None:
                if len(report.ambiguous_samples) < 25:
                    report.ambiguous_samples.append(f"{cand_aa} | {cand_am}")

        out.append(text[cursor:match.start()])
        out.append(replacement)
        cursor = match.end()

    out.append(text[cursor:])
    return "".join(out), report


def collapse_whitespace(text: str) -> str:
    """Collapse runs of spaces and tabs; preserve line structure."""
    text = re.sub(r"[ \t ]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
