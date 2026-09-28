"""Parse one hand-written cook-along log file into a validated record (RQ4, CLAUDE.md §7.4).

One TOML file per cook-along lives in ``data/cook_along/``, named for its date and dish
(``2026-10-04_khao_soi.toml``). The file stem becomes ``cook_along_log.log_key``, so
editing a file and reloading updates its row rather than adding a second one. Files
whose name starts with ``_`` (the template) are skipped.

Keys map one-to-one onto ``cook_along_log`` columns (``db/migrations/016``). Only
``recipe_id`` and ``cook_date`` are required: a cook-along that happened has a dish and
a date. Every other field is optional and an absent one is stored as NULL — "not
recorded", never a guessed value. Unknown keys are an error, so a typo such as
``fidelity_quantites`` fails loudly instead of silently becoming NULL.

**PDPA.** The free-text fields are the researcher's own notes, and a note about cooking
with family can name someone. This module does not redact: a file carrying anything
``redact()`` would strip, or anything ``find_leaks()`` detects, is **refused** with the
field named. Redacting on load would keep the database clean while leaving the
personal data sitting in a file that is meant to be committed; refusing makes the fix
happen at the source. The pattern-based check catches honorific names (นาย, นาง, …),
phone numbers, emails and addresses — it cannot recognise a bare given name with no
honorific, so notes should refer to people by role (ยาย, แม่) as the fieldwork protocol
already requires.
"""

from __future__ import annotations

import datetime
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

from src.ingest.pdpa import find_leaks, redact

FIDELITY_LEVELS = ("survived", "degraded", "lost")

# The five information classes Figure 4 (pipeline fidelity) is a matrix over (§6).
FIDELITY_FIELDS = (
    "fidelity_quantities",
    "fidelity_order",
    "fidelity_technique",
    "fidelity_specificity",
    "fidelity_completeness",
)

TEXT_FIELDS = (
    "missing_ingredients",
    "substitutions_made",
    "normalization_losses",
    "notes",
)


class CookAlongError(ValueError):
    """A cook-along file that cannot be loaded as written."""


@dataclass(frozen=True)
class CookAlongEntry:
    """One row of ``cook_along_log``, validated."""

    log_key: str
    recipe_id: int
    cook_date: datetime.date
    missing_ingredients: str | None = None
    substitutions_made: str | None = None
    normalization_losses: str | None = None
    result_recognizable: bool | None = None
    classifier_gets_wrong: bool = False
    fidelity_quantities: str | None = None
    fidelity_order: str | None = None
    fidelity_technique: str | None = None
    fidelity_specificity: str | None = None
    fidelity_completeness: str | None = None
    notes: str | None = None


# Every key a file may carry: all entry fields except log_key, which comes from the name.
ALLOWED_KEYS = frozenset(f.name for f in fields(CookAlongEntry)) - {"log_key"}


def parse_entry(log_key: str, data: dict[str, object]) -> CookAlongEntry:
    """Validate a parsed TOML mapping. Raises ``CookAlongError`` naming the problem."""
    unknown = sorted(set(data) - ALLOWED_KEYS)
    if unknown:
        raise CookAlongError(f"{log_key}: unknown key(s) {unknown}")

    recipe_id = data.get("recipe_id")
    if not isinstance(recipe_id, int) or isinstance(recipe_id, bool):
        raise CookAlongError(f"{log_key}: recipe_id is required and must be an integer")

    cook_date = data.get("cook_date")
    # TOML dates parse to datetime.date; a datetime (date plus time) is also a date
    # subclass and is not what this field means.
    if not isinstance(cook_date, datetime.date) or isinstance(cook_date, datetime.datetime):
        raise CookAlongError(
            f"{log_key}: cook_date is required and must be a bare TOML date (2026-10-04)"
        )

    for key in ("result_recognizable", "classifier_gets_wrong"):
        if key in data and not isinstance(data[key], bool):
            raise CookAlongError(f"{log_key}: {key} must be true or false")

    for key in FIDELITY_FIELDS:
        if key in data and data[key] not in FIDELITY_LEVELS:
            raise CookAlongError(
                f"{log_key}: {key} = {data[key]!r}; must be one of {FIDELITY_LEVELS}"
            )

    for key in TEXT_FIELDS:
        if key not in data:
            continue
        value = data[key]
        if not isinstance(value, str):
            raise CookAlongError(f"{log_key}: {key} must be a string")
        _, report = redact(value)
        leaks = find_leaks(value)
        if report.total or leaks:
            # Do not echo the matched text: it is the personal data being refused.
            classes = sorted(set(leaks) | {c for c, col in report.COLUMNS.items()
                                           if getattr(report, col)})
            raise CookAlongError(
                f"{log_key}: {key} contains personal data ({', '.join(classes)}). "
                "Refer to people by role, not name, and remove contact details."
            )

    values = {k: v for k, v in data.items() if not (isinstance(v, str) and not v.strip())}
    return CookAlongEntry(log_key=log_key, **values)  # type: ignore[arg-type]  # validated above


def read_entry(path: Path) -> CookAlongEntry:
    """Parse and validate one cook-along file."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise CookAlongError(f"{path.stem}: not valid TOML — {e}") from e
    return parse_entry(path.stem, data)


def log_files(directory: Path) -> list[Path]:
    """The cook-along files in ``directory``, sorted, excluding ``_``-prefixed ones."""
    return sorted(p for p in directory.glob("*.toml") if not p.name.startswith("_"))
