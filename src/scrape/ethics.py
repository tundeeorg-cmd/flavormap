"""Rule 1 (`docs/scraping_rules.md`) — ethics first, enforced in code.

Two halves:

* :func:`require_cleared` is the **gate**. No page of a source is fetched by
  :mod:`src.scrape.base` until ``ETHICS.md``'s source-audit table has a row for it that
  is dated, records a robots.txt result *and* a Terms-of-Service result, and carries a
  decided go (``✅``) in its Decision cell. "HD-3 open", "pending", "Dropped" and
  "Blocked" all refuse. The table is the authority; this module only reads it, so the
  gate cannot be opened by editing code.
* :func:`audit_site` is the ``--audit`` stage. It fetches robots.txt and the ToS page
  (politely, through :mod:`src.scrape.conduct`), quotes every clause that touches
  automated access or reuse, and writes a dated report plus a *proposed* table row. It
  never edits ``ETHICS.md`` and never writes a decision: the Decision cell is HD-3's and
  the researcher's. If any quoted clause reads as a prohibition, the audit says STOP and
  exits non-zero — a keyword match is not a legal reading, so it stops for a human one.
"""

from __future__ import annotations

import re
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import httpx
from selectolax.parser import HTMLParser

from src.config import DOCS_DIR, REPO_ROOT
from src.scrape.conduct import PoliteFetcher

ETHICS_PATH = REPO_ROOT / "ETHICS.md"
AUDIT_DIR = DOCS_DIR / "source_audits"

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_UNRESOLVED = re.compile(r"^\s*(?:|—|-|pending|not fetched|n/?a|tbd|\?)\s*$", re.I)
_DECIDED_GO = "✅"


class EthicsGateError(SystemExit):
    """No cleared ETHICS.md row for this source. Nothing may be fetched."""


@dataclass(frozen=True)
class AuditRow:
    source_id: str
    domain: str
    robots: str
    disallowed: str
    tos: str
    audited_on: date
    decision: str


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def audit_rows(text: str) -> dict[str, list[str]]:
    """Raw cells of the source-audit table, keyed by source_id (backticks stripped)."""
    rows: dict[str, list[str]] = {}
    in_table = False
    for line in text.splitlines():
        if line.startswith("| source_id"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                break
            cells = _cells(line)
            if set(cells[0]) <= {"-", ":"}:
                continue
            rows[cells[0].strip("`* ")] = cells
    return rows


def require_cleared(source_id: str, ethics_path: Path = ETHICS_PATH) -> AuditRow:
    """Return the source's audit row, or refuse (raise) with the reason it is not cleared."""
    rows = audit_rows(ethics_path.read_text(encoding="utf-8"))
    cells = rows.get(source_id)
    if cells is None:
        raise EthicsGateError(
            f"ETHICS.md has no audit row for {source_id!r}. Run --audit, add the dated row, "
            "and get the HD-3 decision before any crawl (rule 1)."
        )
    if len(cells) < 7:
        raise EthicsGateError(f"ETHICS.md row for {source_id!r} is malformed: {cells}")
    sid, domain, robots, disallowed, tos, audited, decision = cells[:7]
    problems: list[str] = []
    match = _DATE.search(audited)
    if not match:
        problems.append("the row is not dated")
    if _UNRESOLVED.match(robots):
        problems.append("no robots.txt result")
    if _UNRESOLVED.match(tos):
        problems.append("no Terms-of-Service result")
    if _DECIDED_GO not in decision:
        problems.append(f"no decided go in the Decision cell ({decision[:80]!r})")
    if problems:
        raise EthicsGateError(
            f"{source_id!r} is not cleared to crawl: " + "; ".join(problems) + ". Stop (rule 1)."
        )
    assert match is not None
    return AuditRow(sid.strip("`* "), domain, robots, disallowed, tos,
                    date.fromisoformat(match.group(0)), decision)


# ── --audit ──────────────────────────────────────────────────────────────────

# A clause is quoted if it mentions automated access or reuse; it is flagged as a
# possible prohibition if the same clause also carries a negation.
_ACCESS = re.compile(
    r"automat\w*|robot|spider|crawl\w*|scrap\w*|data[- ]mining|harvest\w*|"
    r"reproduc\w*|republish\w*|redistribut\w*|copy|copie[sd]|commercial|"
    r"โปรแกรมอัตโนมัติ|บอท|ดึงข้อมูล|คัดลอก|ทำซ้ำ|เผยแพร่ซ้ำ|ดัดแปลง|ลิขสิทธิ์|เชิงพาณิชย์",
    re.I,
)
_NEGATION = re.compile(
    r"\bnot\b|\bno\b|prohibit\w*|forbid\w*|may not|must not|shall not|without (?:the )?"
    r"(?:prior |express )?(?:written )?(?:permission|consent)|"
    r"ห้าม|ไม่อนุญาต|โดยไม่ได้รับอนุญาต|ไม่ได้รับอนุญาต|สงวนสิทธิ์",
    re.I,
)
_CLAUSE_SPLIT = re.compile(r"(?<=[.!?;])\s+|\n+")
MAX_CLAUSE_CHARS = 400


@dataclass
class Clause:
    text: str
    possible_prohibition: bool


@dataclass
class AuditReport:
    source_id: str
    base_url: str
    audited_on: date
    robots_status: int | None = None
    robots_text: str = ""
    robots_root_allowed: bool | None = None
    tos_url: str | None = None
    tos_status: int | None = None
    clauses: list[Clause] = field(default_factory=list)

    @property
    def must_stop(self) -> bool:
        return self.robots_root_allowed is False or any(
            c.possible_prohibition for c in self.clauses
        )


def relevant_clauses(text: str) -> list[Clause]:
    """Every clause of a ToS text that touches automated access or reuse, verbatim."""
    out: list[Clause] = []
    seen: set[str] = set()
    for raw in _CLAUSE_SPLIT.split(text):
        clause = " ".join(raw.split())
        if not clause or clause in seen or not _ACCESS.search(clause):
            continue
        seen.add(clause)
        out.append(Clause(clause[:MAX_CLAUSE_CHARS], bool(_NEGATION.search(clause))))
    return out


def page_text(html: str) -> str:
    tree = HTMLParser(html)
    for tag in tree.css("script, style, noscript"):
        tag.decompose()
    body = tree.body
    return body.text(separator="\n") if body is not None else ""


def audit_site(
    client: httpx.Client,
    source_id: str,
    base_url: str,
    tos_url: str | None,
    ua: str,
    today: date | None = None,
) -> AuditReport:
    """Fetch robots.txt and the ToS page and quote what matters. Writes nothing."""
    report = AuditReport(source_id, base_url, today or date.today(), tos_url=tos_url)
    response = client.get(f"{base_url}/robots.txt")
    report.robots_status = response.status_code
    parser = urllib.robotparser.RobotFileParser()
    if response.status_code == 200:
        report.robots_text = response.text
        parser.parse(response.text.splitlines())
    else:
        parser.parse([])
    report.robots_root_allowed = parser.can_fetch(ua, base_url + "/")
    if tos_url and report.robots_root_allowed:
        fetcher = PoliteFetcher(client, parser, ua)
        fetcher.note_request()
        tos = fetcher.get(tos_url)
        report.tos_status = tos.status_code if tos is not None else None
        if tos is not None and tos.status_code == 200:
            report.clauses = relevant_clauses(page_text(tos.text))
    return report


def render_audit(report: AuditReport) -> str:
    d = report.audited_on.isoformat()
    robots = (
        "root allowed for our UA" if report.robots_root_allowed
        else "**root DISALLOWED for our UA**"
    )
    if not report.tos_url:
        tos = "no ToS URL supplied — locate one by hand, or record that none exists"
    elif report.tos_status != 200:
        status = report.tos_status if report.tos_status is not None else "disallowed or not fetched"
        tos = f"ToS page not retrieved ({status}) — read it by hand"
    elif not report.clauses:
        tos = "ToS read; no clause on automated access or reuse found"
    else:
        flagged = sum(c.possible_prohibition for c in report.clauses)
        tos = f"{len(report.clauses)} relevant clauses, {flagged} read as possible prohibitions"
    lines = [
        f"# Source audit — `{report.source_id}` — {d}",
        "",
        "Generated by `--audit` (`src/scrape/ethics.py`). **The Decision is HD-3's and "
        "the researcher's.** Nothing here clears the source.",
        "",
        f"- Base URL: {report.base_url}",
        f"- robots.txt: HTTP {report.robots_status}; {robots}",
        f"- Terms of Service: {report.tos_url or '—'} — {tos}",
        "",
        "## robots.txt, verbatim",
        "",
        "```",
        report.robots_text.strip() or "(empty or not served)",
        "```",
        "",
        "## Terms-of-Service clauses on automated access or reuse, verbatim",
        "",
    ]
    if report.clauses:
        for c in report.clauses:
            flag = "**⚠ possible prohibition** — " if c.possible_prohibition else ""
            lines.append(f"> {flag}{c.text}")
            lines.append("")
    else:
        lines += ["(none found)", ""]
    lines += [
        "## Proposed `ETHICS.md` row",
        "",
        "Paste into the source-audit table after reading the clauses above yourself. The "
        "Decision cell stays `HD-3 open` until the researcher decides; `--pilot` and "
        "`--full` refuse until it carries `✅`.",
        "",
        "```",
        f"| `{report.source_id}` | `{report.base_url.split('//')[-1]}` | {robots} | "
        f"see docs/source_audits/{report.source_id}_{d}.md | {tos} | {d} | **HD-3 open** |",
        "```",
        "",
    ]
    if report.must_stop:
        lines += [
            "## STOP",
            "",
            "robots.txt disallows us, or a ToS clause reads as forbidding automated "
            "collection or reuse. No scraper is written for this source until the "
            "researcher has read the clauses and recorded a decision.",
            "",
        ]
    return "\n".join(lines)


def write_audit(report: AuditReport, directory: Path = AUDIT_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{report.source_id}_{report.audited_on.isoformat()}.md"
    path.write_text(render_audit(report), encoding="utf-8")
    return path
