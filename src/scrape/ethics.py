"""The ethics gate (docs/scraping_rules.md §1).

`ETHICS.md` carries a **scraper audit register**: one dated row per audit, per source.

    | source_id | site | date | robots.txt | terms of service | decision |

`--audit` appends a row whose decision is ``pending``, and writes the evidence (the
robots.txt result and short quotes of any flagged ToS clauses) to
``data/coverage/<source>_audit.md``. **Only the researcher changes a decision to
``go``** (or ``no-go``): whether a site's terms permit collection is a judgement, the
source go/no-go gate in CLAUDE.md §9.

`require_go` is what makes that binding: `--pilot` and `--full` refuse to run unless the
**latest** row for the source says ``go``. A later ``pending`` or ``no-go`` row closes a
source that was open.

`flag_tos_clauses` only *finds* clauses worth reading (automated access, scraping,
copying, reuse, in English and Thai) and quotes them briefly. It never concludes that a
site permits or forbids anything.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from pathlib import Path

from src.config import REPO_ROOT

ETHICS_PATH = REPO_ROOT / "ETHICS.md"
REGISTER_HEADING = "## Scraper audit register"
REGISTER_HEADER = "| source_id | site | date | robots.txt | terms of service | decision |"

# Words that mark a ToS clause the researcher must read. Finding one is not a verdict.
TOS_KEYWORDS = (
    "automat", "scrap", "crawl", "robot", "spider", "bot ", "data mining", "harvest",
    "reproduc", "copy", "redistribut", "commercial",
    "อัตโนมัติ", "บอท", "โปรแกรม", "ดึงข้อมูล", "คัดลอก", "ทำซ้ำ", "ดัดแปลง",
    "เผยแพร่", "ห้าม", "ลิขสิทธิ์",
)
MAX_QUOTE_CHARS = 200


class EthicsGateClosed(SystemExit):
    """The source has no ``go`` decision in the ETHICS.md register. The crawl stops."""


@dataclass(frozen=True)
class AuditRow:
    source_id: str
    site: str
    date: str
    robots: str
    tos: str
    decision: str

    def as_markdown(self) -> str:
        cells = (self.source_id, self.site, self.date, self.robots, self.tos, self.decision)
        return "| " + " | ".join(c.replace("|", "/") for c in cells) + " |"


def read_register(path: Path = ETHICS_PATH) -> list[AuditRow]:
    """Every row of the register, in file order."""
    text = path.read_text(encoding="utf-8")
    if REGISTER_HEADING not in text:
        return []
    section = text.split(REGISTER_HEADING, 1)[1].split("\n## ", 1)[0]
    rows: list[AuditRow] = []
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 6 or cells[0] in ("source_id", "") or set(cells[0]) <= {"-", ":"}:
            continue
        rows.append(AuditRow(*cells))
    return rows


def latest(source_id: str, path: Path = ETHICS_PATH) -> AuditRow | None:
    rows = [r for r in read_register(path) if r.source_id == source_id]
    return rows[-1] if rows else None


def require_go(source_id: str, path: Path = ETHICS_PATH) -> AuditRow:
    """The latest register row for `source_id`, if its decision is ``go``. Otherwise
    raises `EthicsGateClosed`: no crawl without a recorded, dated go."""
    row = latest(source_id, path)
    if row is None:
        raise EthicsGateClosed(
            f"{source_id}: no row in the ETHICS.md scraper audit register. Run --audit "
            "first; the researcher then records the decision.")
    if not row.decision.lower().startswith("go"):
        raise EthicsGateClosed(
            f"{source_id}: the latest ETHICS.md decision ({row.date}) is "
            f"'{row.decision}', not 'go'. Only the researcher changes it.")
    return row


def append_row(row: AuditRow, path: Path = ETHICS_PATH) -> None:
    """Append `row` to the register, creating the section if it does not exist yet."""
    text = path.read_text(encoding="utf-8")
    if REGISTER_HEADING not in text:
        text = (text.rstrip("\n") + f"\n\n{REGISTER_HEADING}\n\n{REGISTER_HEADER}\n"
                "|---|---|---|---|---|---|\n")
        text += row.as_markdown() + "\n"
        path.write_text(text, encoding="utf-8")
        return
    head, rest = text.split(REGISTER_HEADING, 1)
    section, sep, tail = rest.partition("\n## ")
    section = section.rstrip("\n") + "\n" + row.as_markdown() + "\n"
    path.write_text(head + REGISTER_HEADING + section + (("\n" + sep + tail) if sep else ""),
                    encoding="utf-8")


def flag_tos_clauses(text: str) -> list[str]:
    """Short quotes of the sentences in `text` that contain a ToS keyword."""
    sentences = re.split(r"(?<=[.!?。])\s+|\n+", text)
    quotes: list[str] = []
    for s in sentences:
        s = " ".join(s.split())
        if s and any(k in s.lower() for k in TOS_KEYWORDS):
            quotes.append(s if len(s) <= MAX_QUOTE_CHARS else s[: MAX_QUOTE_CHARS - 1] + "…")
    return quotes


def today() -> str:
    return datetime.date.today().isoformat()
