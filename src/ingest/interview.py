"""Read and validate one fieldwork interview file (HD-30, HD-32).

One TOML file per informant in ``data/interviews/``, named for the informant
(``INT_BRM_001.toml``). The directory is gitignored (HD-30): only the blank
``_template.toml`` is tracked. ``_``-prefixed files are skipped.

**What is refused, before anything is written:**

- **No consent.** ``consent_form`` must be explicitly ``true``, and ``consent_date``
  cannot be after ``interview_date``. The ethics rules (CLAUDE.md §7.3) require a signed
  Thai consent form for every interview.
- **Personal data, anywhere.** Every text value, including ingredient lines, is checked
  with ``personal_data_classes()`` and refused, never redacted: the file on disk has to
  be clean at the source. The check catches titled names, phone numbers, emails and
  addresses. It cannot recognise a bare given name, so people are referred to by role
  (ยาย, แม่ค้า), as the fieldwork protocol already requires.
- **Name- or contact-shaped keys** (``name``, ``phone``, ``line_id`` …), and any key not
  on the list: typos fail loudly instead of becoming NULL.
- **Free text over 500 characters** (the archived v2 limit): long answers are where
  identifying detail accumulates. Summarise instead.
- **No district, or any subdistrict.** ``district`` (อำเภอ) is required. A
  subdistrict (ตำบล), village or หมู่ key is refused by name: HD-21 (decided B) keeps
  ตำบล out of the database on both streams.
- **An ID that disagrees with its province.** IDs are ``INT_{PROVINCE}_{NNN}``, with one
  prefix per HD-32 fieldwork province (NMA, BRM).
- **An unknown or duplicate dish number.** Dishes carry an explicit ``dish_no``, so
  reordering the file never re-keys a dish.

**What is never done here.** No dish is matched to an official dish by name
(``official_recipe_id`` is entered by the researcher, HD-30 (1)). No endangerment level
is inferred from a cook's words (``cook_status_level`` is coded under HD-11, HD-30 (2)).
Ingredients are kept exactly as recorded; canonicalisation (HD-6) maps them later.
"""

from __future__ import annotations

import datetime
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from src.clean.lexicon import key
from src.ingest.pdpa import personal_data_classes

# HD-32: the two fieldwork provinces, and each one's informant-ID prefix.
FIELDWORK_PROVINCES: dict[str, str] = {"TH-30": "NMA", "TH-31": "BRM"}

INFORMANT_ID = re.compile(r"INT_([A-Z]{3})_(\d{3})")
MAX_TEXT = 500
AGE_BRACKETS = ("lt40", "40_60", "gt60")
ACQUISITION_MODES = ("grown", "foraged", "market", "packaged")
STATUS_LEVELS = ("lost", "near_lost", "transmitted")

# HD-21 (decided B, 2026-09-29): no geography finer than district, on either stream.
FINER_THAN_DISTRICT = re.compile(r"(subdistrict|tambo|ตำบล|village|หมู่บ้าน|^moo$|หมู่)")

# Keys that would carry a person's identity or contact details. Refused by name as well
# as by being off the allowed list, so the error says why.
FORBIDDEN_KEY = re.compile(
    r"(^|_)(name|first_name|last_name|surname|nickname|phone|tel|mobile|email|line|"
    r"line_id|facebook|address|house|gps|lat|lon|photo)($|_)"
)

INFORMANT_KEYS = frozenset({
    "informant_id", "province_code", "district", "age_bracket", "role",
    "acquisition_mode", "consent_form", "consent_date", "interview_date", "dishes",
})
DISH_KEYS = frozenset({
    "dish_no", "name_th", "ingredients", "official_recipe_id", "cook_status_verbatim",
    "cook_status_level", "distinctiveness_claim", "stated_absence",
    "stated_substitutions", "differs_from_bangkok", "validation_notes",
})
DISH_TEXT = ("name_th", "cook_status_verbatim", "distinctiveness_claim", "stated_absence",
             "stated_substitutions", "differs_from_bangkok", "validation_notes")


class InterviewError(ValueError):
    """An interview file that cannot be loaded as written."""


@dataclass(frozen=True)
class Dish:
    dish_no: int
    name_th: str
    ingredients: list[str]
    official_recipe_id: int | None = None
    cook_status_verbatim: str | None = None
    cook_status_level: str | None = None
    distinctiveness_claim: str | None = None   # interview Q4
    stated_absence: str | None = None          # interview Q9 (RQ2 validation)
    stated_substitutions: str | None = None
    differs_from_bangkok: str | None = None
    validation_notes: str | None = None


@dataclass(frozen=True)
class Interview:
    informant_id: str
    province_code: str
    district: str | None
    age_bracket: str | None
    role: str | None
    acquisition_mode: str | None
    consent_form: bool
    consent_date: datetime.date
    interview_date: datetime.date
    dishes: list[Dish] = field(default_factory=list)

    def dish_key(self, dish: Dish) -> str:
        return f"{self.informant_id}/{dish.dish_no}"


def _is_date(v: object) -> bool:
    return isinstance(v, datetime.date) and not isinstance(v, datetime.datetime)


def _check_keys(where: str, data: dict[str, object], allowed: frozenset[str],
                errors: list[str]) -> None:
    for k in sorted(data):
        if FINER_THAN_DISTRICT.search(k.lower()):
            errors.append(f"{where}: key '{k}' is finer than district; HD-21 keeps "
                          "subdistrict (ตำบล) out of the database")
        elif FORBIDDEN_KEY.search(k.lower()) and k not in allowed:
            errors.append(f"{where}: key '{k}' looks like personal data; not allowed")
        elif k not in allowed:
            errors.append(f"{where}: unknown key '{k}'")


def _check_text(where: str, value: object, errors: list[str]) -> str | None:
    """Validate one free-text value; return it normalised, or None if blank."""
    if value is None:
        return None
    if not isinstance(value, str):
        errors.append(f"{where} must be a string")
        return None
    text = key(value)
    if len(text) > MAX_TEXT:
        errors.append(f"{where} is {len(text)} characters; the limit is {MAX_TEXT}")
    if classes := personal_data_classes(text):
        # Class names only: never echo the personal data being refused.
        errors.append(f"{where} contains personal data ({', '.join(classes)})")
    return text or None


def parse_interview(stem: str, data: dict[str, object]) -> Interview:
    """Validate a parsed TOML mapping. Raises one ``InterviewError`` listing every
    problem, so a single run shows everything to fix."""
    errors: list[str] = []
    _check_keys(stem, data, INFORMANT_KEYS, errors)

    informant_id = data.get("informant_id")
    province = data.get("province_code")
    m = INFORMANT_ID.fullmatch(informant_id) if isinstance(informant_id, str) else None
    if m is None:
        errors.append(f"{stem}: informant_id must look like INT_BRM_001")
    elif informant_id != stem:
        errors.append(f"{stem}: file name must match informant_id {informant_id}")
    if province not in FIELDWORK_PROVINCES:
        errors.append(f"{stem}: province_code must be one of the HD-32 fieldwork provinces "
                      f"{sorted(FIELDWORK_PROVINCES)}")
    elif m is not None and m.group(1) != FIELDWORK_PROVINCES[str(province)]:
        errors.append(f"{stem}: ID prefix {m.group(1)} does not match {province} "
                      f"(expected INT_{FIELDWORK_PROVINCES[str(province)]}_…)")

    if data.get("consent_form") is not True:
        errors.append(f"{stem}: consent_form must be explicitly true; no interview loads "
                      "without signed consent")
    consent, interview = data.get("consent_date"), data.get("interview_date")
    if not _is_date(consent):
        errors.append(f"{stem}: consent_date is required (a bare TOML date)")
    if not _is_date(interview):
        errors.append(f"{stem}: interview_date is required (a bare TOML date)")
    if _is_date(consent) and _is_date(interview) and consent > interview:  # type: ignore[operator]
        errors.append(f"{stem}: consent_date is after interview_date")

    if data.get("age_bracket") not in (None, *AGE_BRACKETS):
        errors.append(f"{stem}: age_bracket must be one of {AGE_BRACKETS}")
    if data.get("acquisition_mode") not in (None, *ACQUISITION_MODES):
        errors.append(f"{stem}: acquisition_mode must be one of {ACQUISITION_MODES}")
    district = _check_text(f"{stem}: district", data.get("district"), errors)
    if not district:
        errors.append(f"{stem}: district (อำเภอ) is required")
    role = _check_text(f"{stem}: role", data.get("role"), errors)

    dishes: list[Dish] = []
    raw_dishes = data.get("dishes")
    if not isinstance(raw_dishes, list) or not raw_dishes:
        errors.append(f"{stem}: at least one [[dishes]] entry is required")
        raw_dishes = []
    seen: set[int] = set()
    for i, d in enumerate(raw_dishes, 1):
        where = f"{stem}: dish {i}"
        if not isinstance(d, dict):
            errors.append(f"{where} is not a table")
            continue
        _check_keys(where, d, DISH_KEYS, errors)
        no = d.get("dish_no")
        if not isinstance(no, int) or isinstance(no, bool) or no < 1:
            errors.append(f"{where}: dish_no must be a positive integer")
            continue
        if no in seen:
            errors.append(f"{where}: dish_no {no} is used twice")
        seen.add(no)
        where = f"{stem}: dish_no {no}"
        texts = {k: _check_text(f"{where}: {k}", d.get(k), errors) for k in DISH_TEXT}
        if not texts["name_th"]:
            errors.append(f"{where}: name_th is required")
        ingredients = d.get("ingredients", [])
        if not isinstance(ingredients, list) or not all(isinstance(x, str) for x in ingredients):
            errors.append(f"{where}: ingredients must be a list of strings")
            ingredients = []
        clean_ingredients = [
            t for n, x in enumerate(ingredients, 1)
            if (t := _check_text(f"{where}: ingredient {n}", x, errors))
        ]
        official = d.get("official_recipe_id")
        if official is not None and (not isinstance(official, int) or isinstance(official, bool)):
            errors.append(f"{where}: official_recipe_id must be an integer or left out")
        level = d.get("cook_status_level")
        if level is not None and level not in STATUS_LEVELS:
            errors.append(f"{where}: cook_status_level must be one of {STATUS_LEVELS} "
                          "or left out until coded (HD-11)")
        dishes.append(Dish(
            dish_no=no, name_th=texts["name_th"] or "", ingredients=clean_ingredients,
            official_recipe_id=official if isinstance(official, int) else None,
            cook_status_verbatim=texts["cook_status_verbatim"],
            cook_status_level=level if isinstance(level, str) else None,
            distinctiveness_claim=texts["distinctiveness_claim"],
            stated_absence=texts["stated_absence"],
            stated_substitutions=texts["stated_substitutions"],
            differs_from_bangkok=texts["differs_from_bangkok"],
            validation_notes=texts["validation_notes"],
        ))

    if errors:
        raise InterviewError("\n".join(errors))
    return Interview(
        informant_id=str(informant_id), province_code=str(province), district=district,
        age_bracket=data.get("age_bracket"),  # type: ignore[arg-type]
        role=role,
        acquisition_mode=data.get("acquisition_mode"),  # type: ignore[arg-type]
        consent_form=True,
        consent_date=consent,  # type: ignore[arg-type]
        interview_date=interview,  # type: ignore[arg-type]
        dishes=sorted(dishes, key=lambda x: x.dish_no),
    )


def read_interview(path: Path) -> Interview:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise InterviewError(f"{path.stem}: not valid TOML — {e}") from e
    return parse_interview(path.stem, data)


def interview_files(directory: Path) -> list[Path]:
    """Interview files in `directory`, sorted, excluding ``_``-prefixed ones."""
    return sorted(p for p in directory.glob("*.toml") if not p.name.startswith("_"))
