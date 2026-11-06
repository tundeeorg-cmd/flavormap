"""T1.24: audit a DH2027 draft — word count, reference count, and every number traced.

    uv run python -m scripts.paper_audit [--draft paper/dh2027/draft.md] [--write]
                                                                    (make paper-audit)

Reads a Markdown draft and ``paper/dh2027/numbers.md``. Writes nothing unless ``--write``,
which fills numbers.md's two "Submission checks" lines (word count, references) with the
counts, the draft's file name and the commit. It never edits the draft.

**Word count** (DH2027 CFP: 1,000–1,250 words, captions included). Counted: body prose,
headings and figure/table captions. Not counted: Markdown table rows (lines starting
``|``; the outline says counts in table cells do not count), the reference section (the
heading named ``References`` or ``Bibliography`` to the next heading of the same or higher
level), the AI disclosure section, the title block before the first ``##`` heading,
fenced code, HTML comments and the YAML front matter. Words are whitespace tokens
holding a letter or digit; author placeholders (``[TBD: …]``, ``[ORIGIN STORY …]``: a
bracket opening with a capitalised tag) are left out and listed, here and in the
reference count. A Thai run is split with PyThaiNLP ``newmm`` and each Thai word counts
once, so a quoted Thai question is not one "word". Both totals are printed. Numbers
spelled out in words ("three", "twelve") are not audited.

**References**: one per non-empty list item, or per non-empty paragraph when the section
has no list, inside the reference section.

**Number audit**: every number in the counted prose (captions included) is looked for in
numbers.md's filled values (backticked values and numbers on lines without ``[TBD``).
A draft number matches if a numbers.md value equals it after removing thousands commas
and ``%``, or rounds to it at the draft's decimal places (0.5678 → 0.57; rounding only for
numbers of two or more digits, since 0.6 would match too much). Values come from the value
cell of filled table rows, before the first `` · ``. Not checked,
and listed separately so a reader can see why:

- labels: a number glued to letters or after Figure/Table/Section/RQ/Q/HD/T
  (``RQ1``, ``Figure 6``, ``HD-44``);
- citation years: four digits 1900–2099 inside parentheses or after ``et al.``.

Everything else that does not match is **untraced**. T1.24's done-when is zero untraced.
The audit only finds; whether a number is right is the researcher's.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

from src.config import REPO_ROOT

PAPER_DIR = REPO_ROOT / "paper" / "dh2027"
DRAFT = PAPER_DIR / "draft.md"
NUMBERS = PAPER_DIR / "numbers.md"
WORD_RANGE = (1_000, 1_250)

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_REF_HEADING = re.compile(r"^(references|bibliography|works cited)\b", re.I)
# Not counted (outline: "AI disclosure (not counted)"); its numbers are not audited.
_UNCOUNTED_HEADING = re.compile(r"^ai(-use| use)? disclosure\b", re.I)
_THAI = re.compile(r"[฀-๿]+")
_WORD = re.compile(r"[^\s]*[^\W_][^\s]*", re.U)
_NUMBER = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(%?)(?![\w.]\w)")
_LABEL_BEFORE = re.compile(
    r"(?:\b(?:figure|fig\.|table|section|question|rq|q|gate|g|t|l)|§|\bhd-)\s*$", re.I)
# An author placeholder: a bracket opening with a capitalised tag, e.g. "[TBD: …]",
# "[ORIGIN STORY — …]", "[AUTHOR: …]". Not prose: left out of words and numbers, listed.
_PLACEHOLDER = re.compile(r"\[[A-Z][A-Z ]{2,}[^\]]*\]")


@dataclass
class Draft:
    counted: list[str]                      # lines whose words count
    references: list[str]                   # lines of the reference section
    excluded_tables: int = 0
    counted_at: list[int] = field(default_factory=list)   # file line of each counted line
    placeholders: list[tuple[int, str]] = field(default_factory=list)


def split(text: str) -> Draft:
    """Separate counted prose from tables, code, comments, front matter and references."""
    # Comments become blank lines, so reported line numbers stay the file's own.
    text = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":           # YAML front matter
        start = next((i for i, ln in enumerate(lines[1:], 1) if ln.strip() == "---"), 0) + 1
    out = Draft([], [])
    in_code, ref_level, skip_level = False, 0, 0
    in_body = False          # the title block before the first "## " heading is not counted
    for lineno, ln in enumerate(lines[start:], start + 1):
        if ln.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        h = _HEADING.match(ln)
        if h:
            level, title = len(h.group(1)), h.group(2).strip()
            if level >= 2:
                in_body = True
            if ref_level and level <= ref_level:
                ref_level = 0
            if skip_level and level <= skip_level:
                skip_level = 0
            if _REF_HEADING.match(title):
                ref_level = level
                continue
            if _UNCOUNTED_HEADING.match(title):
                skip_level = level
                continue
        if skip_level or not in_body:
            continue
        if ref_level:
            for m in _PLACEHOLDER.finditer(ln):
                out.placeholders.append((lineno, m.group(0)[:60]))
            out.references.append(_PLACEHOLDER.sub("", ln))
        elif ln.lstrip().startswith("|"):
            out.excluded_tables += 1
        else:
            for m in _PLACEHOLDER.finditer(ln):
                out.placeholders.append((lineno, m.group(0)[:60]))
            ln = _PLACEHOLDER.sub(" ", ln)
            if ln.strip():
                out.counted.append(ln)
                out.counted_at.append(lineno)
    return out


def _plain(line: str) -> str:
    """Markdown markup off: links keep their text, images their alt text."""
    line = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", line)
    line = re.sub(r"^\s*(#{1,6}|[-*+]|\d+\.)\s+", "", line)
    return re.sub(r"[*_`>]", "", line)


def count_words(lines: list[str]) -> tuple[int, int]:
    """(total words, of which Thai words). Thai runs are split with newmm."""
    from pythainlp.tokenize import word_tokenize
    total = thai = 0
    for ln in lines:
        plain = _plain(ln)
        for run in _THAI.findall(plain):
            n = sum(1 for w in word_tokenize(run, engine="newmm") if w.strip())
            thai += n
            total += n
        total += len(_WORD.findall(_THAI.sub(" ", plain)))
    return total, thai


def count_references(lines: list[str]) -> int:
    items = [ln for ln in lines if re.match(r"^\s*([-*+]|\d+\.)\s+\S", ln)]
    if items:
        return len(items)
    paragraphs, current = 0, False
    for ln in lines:
        if ln.strip() and not current:
            paragraphs += 1
        current = bool(ln.strip())
    return paragraphs


@dataclass
class NumberAudit:
    traced: list[str] = field(default_factory=list)
    untraced: list[tuple[int, str, str]] = field(default_factory=list)  # (line, number, context)
    labels: list[str] = field(default_factory=list)
    years: list[str] = field(default_factory=list)


def _decimal(token: str) -> Decimal | None:
    try:
        return Decimal(token.replace(",", "").rstrip("%"))
    except InvalidOperation:
        return None


def known_values(numbers_md: str) -> set[Decimal]:
    """Every number in the value cell of a filled numbers.md table row, up to the first
    `` · `` (after it come the output file, commit and date, which are not values)."""
    out: set[Decimal] = set()
    for ln in numbers_md.splitlines():
        cells = ln.split("|")
        if not ln.lstrip().startswith("|") or len(cells) < 4 or "[TBD" in ln:
            continue
        value = cells[2].split(" · ")[0]
        for m in _NUMBER.finditer(value):
            d = _decimal(m.group(1) + (m.group(2) or ""))
            if d is not None:
                out.add(d)
    return out


def _places(d: Decimal) -> int:
    exponent = d.as_tuple().exponent
    return -exponent if isinstance(exponent, int) and exponent < 0 else 0


def matches(token: str, known: set[Decimal]) -> bool:
    """Equal, or `known` rounds (half up) to `token` at the token's decimal places."""
    d = _decimal(token)
    if d is None:
        return False
    if d in known:
        return True
    if len(d.as_tuple().digits) < 2:   # 0.6 would "match" too many values by rounding
        return False
    places = _places(d)
    quantum = Decimal(1).scaleb(-places)
    return any(k.quantize(quantum, rounding=ROUND_HALF_UP) == d
               for k in known if _places(k) > places)


def audit_numbers(lines: list[str], known: set[Decimal],
                  at: list[int] | None = None) -> NumberAudit:
    """`at`: the file line of each entry of `lines`, for the report."""
    out = NumberAudit()
    for idx, ln in enumerate(lines):
        i = at[idx] if at else idx + 1
        plain = _plain(ln)
        for m in _NUMBER.finditer(plain):
            token = m.group(0)
            before, after = plain[:m.start()], plain[m.end():]
            numbering = not before.strip() and after.startswith(". ")   # "5. Results"
            if (before and before[-1].isalpha()) or (after and after[:1].isalpha()) \
                    or _LABEL_BEFORE.search(before) or numbering:
                out.labels.append(token)
                continue
            if re.fullmatch(r"(19|20)\d\d", token) and (
                    re.search(r"et al\.?,?\s*$", before)
                    or (before.rfind("(") > before.rfind(")"))):
                out.years.append(token)
                continue
            if matches(token, known):
                out.traced.append(token)
            else:
                out.untraced.append((i, token, plain.strip()[:80]))
    return out


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True, cwd=REPO_ROOT).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def write_checks(numbers: Path, draft: Path, words: int, refs: int, day: str) -> None:
    """Fill numbers.md's word-count and reference lines (Submission checks)."""
    text = numbers.read_text(encoding="utf-8")
    src = f"`{draft.name}` · `make paper-audit` · commit {_commit()} · {day}"
    rows = {
        "| Word count, captions included (1,000–1,250) |": f"`{words:,}`",
        "| References verified (count) |": f"`{refs}` counted (verification is the researcher's)",
    }
    out = []
    for ln in text.splitlines():
        for head, value in rows.items():
            if ln.startswith(head):
                ln = f"{head} {value} · {src} |"
        out.append(ln)
    numbers.write_text("\n".join(out) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    import datetime
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--draft", type=Path, default=DRAFT)
    ap.add_argument("--numbers", type=Path, default=NUMBERS)
    ap.add_argument("--write", action="store_true",
                    help="fill numbers.md's word-count and reference lines")
    args = ap.parse_args(argv)
    if not args.draft.exists():
        print(f"no draft at {args.draft}; write it there (or pass --draft) and run again")
        return 1
    draft = split(args.draft.read_text(encoding="utf-8"))
    words, thai = count_words(draft.counted)
    refs = count_references(draft.references)
    audit = audit_numbers(draft.counted, known_values(args.numbers.read_text(encoding="utf-8")),
                          draft.counted_at)
    lo, hi = WORD_RANGE
    status = "within" if lo <= words <= hi else "OUTSIDE"
    print(f"words: {words:,} ({thai} Thai, newmm) — {status} {lo:,}–{hi:,}; "
          f"table rows excluded: {draft.excluded_tables}")
    print(f"references: {refs}")
    print(f"placeholders (not counted): {len(draft.placeholders)}")
    for line, text in draft.placeholders:
        print(f"  line {line}: {text}")
    print(f"numbers: {len(audit.traced)} traced, {len(audit.untraced)} untraced; "
          f"not checked: {len(audit.labels)} labels, {len(audit.years)} citation years")
    for line, token, context in audit.untraced:
        print(f"  UNTRACED line {line}: {token}  — {context}")
    if args.write:
        write_checks(args.numbers, args.draft, words, refs,
                     datetime.date.today().isoformat())
        print(f"wrote word count and reference count into {args.numbers}")
    return 0 if not audit.untraced else 2


if __name__ == "__main__":
    raise SystemExit(main())
