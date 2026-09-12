"""Parse a `culture.gdcatalog.go.th` (Ministry of Culture) dataset CSV.

Written against `thaitastetherapy.csv`'s documented shape — 52 rows, 16 columns,
UTF-8 with a BOM — but the column lists below are what make this module specific to
that dataset, not the row count.

**PDPA.** Seven columns are a named individual's contact detail:
``ownerprefix``, ``ownername``, ``ownersurname`` (a person), ``address`` (house
number, moo, tambon, amphoe), ``gps`` (their home or shop, to six decimal places —
sub-provincial precision is analytically tempting and is also a home address in a
different notation), ``picowner`` and ``picadress`` (Google Drive links to photos of
the person and their premises). :func:`drop_pii` removes them by construction: it
whitelist-selects the six analytical columns rather than blacklisting the seven PII
ones, so a column neither list has ever named — a schema change upstream, an eleventh
personal-data field the auditor missed — is dropped too, not shipped by default.

**Never fetched.** No function in this module follows a URL. ``picowner`` and
``picadress`` are Google Drive links and Rule 8 forbids storing them at all, which
also means never resolving them to see what they point to.

**Ingredient extraction from `material`.** The field is documented as 17–4,878
characters, three observed shapes: a clean space-separated list, a numbered list
(``1.หอม 2.กระเทียม``), and full prose with ingredients embedded in narrative,
sometimes with literal ``\\n`` sequences (two characters, backslash then n — not an
actual line break). :func:`classify_material` sorts a row into one of these by shape;
:func:`extract_ingredients` extracts for the two structured shapes and reports prose
rows as unparsed rather than guessing at them. No row is silently dropped either way —
see :class:`IngestReport`.

**Region.** The source's own ``region`` column uses a four-way Thai scheme that merges
Central and East into one label (``ภาคกลางและตะวันออก``). Mapping it onto this
project's canonical `provinces.region4` is a judgment call flagged in
``docs/decisions.md`` and is deliberately NOT made here: the raw string is carried
through unchanged in a loader's ``parsed_json``, never collapsed into a canonical
region column by this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

#: Government-published, but a distinct programme from the 231 one-province-one-menu
#: PDFs (different selection criteria) — never merged into one undifferentiated
#: "official" bucket. See `recipes.source_programme` (migration 022).
SOURCE_PROGRAMME = "thai_taste_therapy"

#: A named individual (prefix/given/surname), their address, their GPS coordinates
#: (home or shop, six decimal places), and two Google Drive links to photos of them
#: and their premises. Every one of these is dropped at parse time, before the first
#: database write — not at export, and never "kept internally for provenance".
PII_COLUMNS: tuple[str, ...] = (
    "ownerprefix",
    "ownername",
    "ownersurname",
    "address",
    "gps",
    "picowner",
    "picadress",
)

#: The only columns this project keeps from the source CSV. A whitelist, not the
#: complement of PII_COLUMNS — the CSV has 16 columns and only 13 are named across the
#: two lists; the other three are dropped by omission, exactly as it should be for a
#: column this project has never had a reason to look at.
KEEP_COLUMNS: tuple[str, ...] = (
    "region",
    "province",
    "foodname",
    "originalfoodname",
    "otherfoodname",
    "material",
)


@dataclass
class DropReport:
    """What was dropped from the source CSV, so a reviewer can see rule 8 fired."""

    source_columns: tuple[str, ...]
    kept_columns: tuple[str, ...]
    dropped_columns: tuple[str, ...]
    pii_columns_present: tuple[str, ...]
    pii_columns_missing: tuple[str, ...]


def read_raw(path: Path) -> pd.DataFrame:
    """Read the source CSV.

    ``encoding="utf-8-sig"`` — the file carries a UTF-8 BOM, and plain ``"utf-8"``
    leaves the mark attached to the first column's first value, corrupting it.
    ``dtype=str`` and ``keep_default_na=False`` because pandas' numeric/NaN inference
    has no business touching Thai dish names or free-text ingredient fields.
    """
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)


def drop_pii(df: pd.DataFrame) -> tuple[pd.DataFrame, DropReport]:
    """Whitelist-select :data:`KEEP_COLUMNS`. Raises if any of them is missing.

    Never expressed as ``df.drop(columns=PII_COLUMNS)``: a blacklist ships anything
    the list does not name, including a personal-data column nobody has audited yet.
    A whitelist drops it instead, which is the failure mode rule 8 wants.
    """
    missing_keep = tuple(c for c in KEEP_COLUMNS if c not in df.columns)
    if missing_keep:
        raise ValueError(
            f"expected column(s) missing from source CSV, refusing to guess: {missing_keep}"
        )
    clean = df[list(KEEP_COLUMNS)].copy()
    report = DropReport(
        source_columns=tuple(df.columns),
        kept_columns=KEEP_COLUMNS,
        dropped_columns=tuple(c for c in df.columns if c not in KEEP_COLUMNS),
        pii_columns_present=tuple(c for c in PII_COLUMNS if c in df.columns),
        pii_columns_missing=tuple(c for c in PII_COLUMNS if c not in df.columns),
    )
    return clean, report


# ── material-field classification ────────────────────────────────────────────────

#: A numbered-list marker: "1." / "2)" / Thai digits, followed by non-space. Requires
#: at least two to fire — a single leading "1." on an otherwise prose field is not
#: enough to call the whole field a list.
_NUMBERED_MARKER = re.compile(r"(?:^|\s)[0-9๐-๙]{1,2}[.)]\s*(?=\S)")

#: The literal two-character sequence backslash-n, as the source CSV encodes it — not
#: an actual line break. Its presence is a strong prose signal in this corpus.
_LITERAL_BACKSLASH_N = re.compile(r"\\n")

#: Length above which a field is prose regardless of markers. The brief's own
#: distribution (17–4,878 chars, median ~266) puts every clean/numbered example well
#: under this; a field this long is a method description with ingredients embedded.
_PROSE_LENGTH_THRESHOLD = 400

#: A full stop not part of a numbered marker (already stripped by _NUMBERED_MARKER's
#: own match) is a sentence boundary in this corpus, not a list separator.
_SENTENCE_STOP = re.compile(r"[.](?!\d)")

FORMAT_CLEAN_LIST = "clean_list"
FORMAT_NUMBERED_LIST = "numbered_list"
FORMAT_PROSE = "prose"
FORMAT_EMPTY = "empty"


def classify_material(text: str | None) -> str:
    """Classify one `material` field into one of the three observed shapes.

    Heuristic, not a certainty — flagged in `docs/decisions.md` as a hand-checkable
    judgment call rather than something to hand an LLM. Every row this project loads
    also carries its raw `material` text, so a wrong classification is a caption on
    known input, not a silent loss.
    """
    if text is None:
        return FORMAT_EMPTY
    t = text.strip()
    if not t:
        return FORMAT_EMPTY

    if len(_NUMBERED_MARKER.findall(t)) >= 2:
        return FORMAT_NUMBERED_LIST

    if _LITERAL_BACKSLASH_N.search(t):
        return FORMAT_PROSE

    if len(t) > _PROSE_LENGTH_THRESHOLD:
        return FORMAT_PROSE

    tokens = t.split()
    if tokens and not _SENTENCE_STOP.search(t):
        return FORMAT_CLEAN_LIST

    return FORMAT_PROSE


@dataclass
class ExtractionResult:
    """One row's extraction outcome. `items is None` means "not parsed" — read by
    hand, never guessed at."""

    format: str
    items: list[str] | None
    note: str | None = None


def extract_ingredients(text: str | None) -> ExtractionResult:
    """Extract ingredient tokens from a `material` field, or report it as unparsed.

    Numbered-list items containing "/" (e.g. "ตะไคร้/ข่า" — lemongrass OR galangal)
    are kept as one raw token. Splitting them into two ingredients is an
    ingredient-segmentation judgment call in the same class as the region-mapping
    gate below, and it is not made here; see `docs/decisions.md`.
    """
    fmt = classify_material(text)

    if fmt == FORMAT_EMPTY:
        return ExtractionResult(format=fmt, items=[], note="empty material field")

    t = (text or "").strip()

    if fmt == FORMAT_CLEAN_LIST:
        items = [tok for tok in t.split() if tok]
        return ExtractionResult(format=fmt, items=items)

    if fmt == FORMAT_NUMBERED_LIST:
        pieces = _NUMBERED_MARKER.split(t)
        items = [p.strip() for p in pieces if p.strip()]
        return ExtractionResult(format=fmt, items=items)

    # Prose: the brief is explicit that an LLM pass needs asking first, and 52 rows
    # is small enough to read by hand. Reported unparsed, not auto-extracted.
    return ExtractionResult(
        format=fmt, items=None, note="prose format — needs hand review, not auto-extracted"
    )


# ── whole-file report ─────────────────────────────────────────────────────────────

@dataclass
class IngestReport:
    total_rows: int
    format_counts: dict[str, int]
    parsed: list[dict[str, object]]
    unparsed: list[dict[str, object]]
    drop_report: DropReport
    distinct_regions: list[str]


def build_report(path: Path) -> IngestReport:
    """Read, PDPA-drop, classify and extract — the full pass over one CSV.

    Every row appears in exactly one of `parsed` / `unparsed`. Nothing is dropped
    silently; a prose row that cannot be auto-extracted is listed, with its raw
    material text, not discarded.
    """
    raw = read_raw(path)
    clean, drop_report = drop_pii(raw)

    format_counts: dict[str, int] = {}
    parsed: list[dict[str, object]] = []
    unparsed: list[dict[str, object]] = []

    for idx, row in clean.iterrows():
        result = extract_ingredients(row["material"])
        format_counts[result.format] = format_counts.get(result.format, 0) + 1
        record: dict[str, object] = {
            "row": int(idx),
            "region": row["region"],
            "province": row["province"],
            "foodname": row["foodname"],
            "originalfoodname": row["originalfoodname"],
            "otherfoodname": row["otherfoodname"],
            "format": result.format,
        }
        if result.items is None:
            record["material_raw"] = row["material"]
            record["note"] = result.note
            unparsed.append(record)
        else:
            record["ingredients"] = result.items
            parsed.append(record)

    return IngestReport(
        total_rows=len(clean),
        format_counts=format_counts,
        parsed=parsed,
        unparsed=unparsed,
        drop_report=drop_report,
        distinct_regions=sorted(clean["region"].dropna().unique().tolist()),
    )
