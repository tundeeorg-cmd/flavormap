"""Hand-transcribed DCP forms, for documents with no text layer (HD-35).

Nakhon Nayok's three forms (``east_5_1..3.pdf``) are image scans. The researcher chose
hand transcription over OCR. One TOML file per form in ``data/dcp_manual/``, named for
the PDF it transcribes (``east_5_1.toml`` for ``data/raw/dcp_food/east_5_1.pdf``). The
directory is gitignored apart from the blank template: a transcription is DCP-derived
content, which HD-3 keeps out of public release.

**The same fields the parser produces** (``src.ingest.dcp_form.DCPRecord``) and nothing
else: dish name, the dish's province as written in §1.1, district, the ticked category,
occasion and endangerment boxes, and the §4 ingredient rows (name, quantity value and
unit, ที่มา). **There is no field for the informant's name, address or phone**, and a key
that looks like one is refused, as is any text that looks like personal data. Refused,
never redacted, as for the interview and cook-along files.

**Rules that keep a transcription equivalent to a parse:**

- ``province_th`` is §1.1's จังหวัด **as written**. If §1.1 is blank, the field stays out,
  and the file does not load, exactly as a parsed form with no province does not. The
  §1.3 address is never a substitute (that is the open HD-34).
- Category, occasion and endangerment use the form's own option labels and values, the
  same tables the parser maps through. A box not ticked is left out (unknown), never a
  default.
- ``acquisition_mode`` is **not** derived from ที่มา. The parser's keyword mapping
  predates its decision gate (HD-15), and new records do not extend it. ที่มา is kept
  verbatim in ``acquisition_raw``.
"""

from __future__ import annotations

import datetime
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from src.clean.lexicon import key
from src.ingest.dcp_form import DISH_CATEGORIES, OCCASIONS
from src.ingest.pdpa import personal_data_classes

ENDANGERMENT_LEVELS = ("lost", "near_lost", "transmitted")
DOCUMENT = re.compile(r"(central|east|north|northeast|south)_\d+_\d")
MAX_TEXT = 300

RECORD_KEYS = frozenset({
    "dish_name_th", "province_th", "district_th", "dish_category_source", "occasion_th",
    "endangerment", "ingredients", "transcribed_on", "notes",
})
INGREDIENT_KEYS = frozenset({"name_th", "quantity_value", "quantity_unit", "acquisition_raw"})
FORBIDDEN_KEY = re.compile(
    r"(^|_)(name|first_name|surname|informant|submitter|phone|tel|mobile|email|line|"
    r"line_id|address|house|road|postcode|subdistrict|tambon|ตำบล|signature)($|_)"
)


class ManualError(ValueError):
    """A transcription that cannot be loaded as written."""


@dataclass(frozen=True)
class ManualIngredient:
    position: int
    name_th: str
    quantity_value: str | None = None
    quantity_unit: str | None = None
    acquisition_raw: str | None = None


@dataclass(frozen=True)
class ManualRecord:
    document_ref: str            # e.g. "east_5_1.pdf"
    dish_name_th: str
    province_th: str
    district_th: str | None
    dish_category_source: str | None   # the form's own label, e.g. "อาหารคาว"
    dish_category: str | None          # mapped through the parser's table
    occasion_th: str | None
    occasion: str | None
    endangerment: str | None
    transcribed_on: str
    ingredients: list[ManualIngredient] = field(default_factory=list)
    notes: str | None = None


def _text(where: str, value: object, errors: list[str]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        errors.append(f"{where} must be a string")
        return None
    text = key(value)
    if len(text) > MAX_TEXT:
        errors.append(f"{where} is {len(text)} characters; the limit is {MAX_TEXT}")
    if classes := personal_data_classes(text):
        errors.append(f"{where} contains personal data ({', '.join(classes)})")
    return text or None


def _keys(where: str, data: dict[str, object], allowed: frozenset[str],
          errors: list[str]) -> None:
    for k in sorted(data):
        if k in allowed:
            continue
        if FORBIDDEN_KEY.search(k.lower()):
            errors.append(f"{where}: key '{k}' would carry personal data; there is no "
                          "such field, by design")
        else:
            errors.append(f"{where}: unknown key '{k}'")


def parse_manual(stem: str, data: dict[str, object]) -> ManualRecord:
    """Validate one transcription. Raises one ``ManualError`` listing every problem."""
    errors: list[str] = []
    if not DOCUMENT.fullmatch(stem):
        errors.append(f"{stem}: file name must be the DCP document's, e.g. east_5_1.toml")
    _keys(stem, data, RECORD_KEYS, errors)

    dish = _text(f"{stem}: dish_name_th", data.get("dish_name_th"), errors)
    province = _text(f"{stem}: province_th", data.get("province_th"), errors)
    if not dish:
        errors.append(f"{stem}: dish_name_th is required")
    if not province:
        errors.append(f"{stem}: province_th is required: §1.1 จังหวัด exactly as written. "
                      "If §1.1 is blank the form does not load (never the §1.3 address)")
    district = _text(f"{stem}: district_th", data.get("district_th"), errors)

    category_src = data.get("dish_category_source")
    if category_src is not None and category_src not in DISH_CATEGORIES:
        errors.append(f"{stem}: dish_category_source must be one of "
                      f"{sorted(DISH_CATEGORIES)} or left out")
    occasion_th = data.get("occasion_th")
    if occasion_th is not None and occasion_th not in OCCASIONS:
        errors.append(f"{stem}: occasion_th must be one of {sorted(OCCASIONS)} or left out")
    level = data.get("endangerment")
    if level is not None and level not in ENDANGERMENT_LEVELS:
        errors.append(f"{stem}: endangerment must be one of {ENDANGERMENT_LEVELS} or left "
                      "out (unticked, or 'other' ticked)")
    transcribed_on = data.get("transcribed_on")
    if not isinstance(transcribed_on, datetime.date) or isinstance(
        transcribed_on, datetime.datetime
    ):
        errors.append(f"{stem}: transcribed_on is required (a bare TOML date)")
    notes = _text(f"{stem}: notes", data.get("notes"), errors)

    ingredients: list[ManualIngredient] = []
    raw_rows = data.get("ingredients")
    if not isinstance(raw_rows, list) or not raw_rows:
        errors.append(f"{stem}: at least one [[ingredients]] row is required")
        raw_rows = []
    for n, row in enumerate(raw_rows, 1):
        where = f"{stem}: ingredient {n}"
        if not isinstance(row, dict):
            errors.append(f"{where} is not a table")
            continue
        _keys(where, row, INGREDIENT_KEYS, errors)
        name = _text(f"{where} name_th", row.get("name_th"), errors)
        if not name:
            errors.append(f"{where}: name_th is required")
        ingredients.append(ManualIngredient(
            position=n, name_th=name or "",
            quantity_value=_text(f"{where} quantity_value", row.get("quantity_value"), errors),
            quantity_unit=_text(f"{where} quantity_unit", row.get("quantity_unit"), errors),
            acquisition_raw=_text(f"{where} acquisition_raw", row.get("acquisition_raw"), errors),
        ))

    if errors:
        raise ManualError("\n".join(errors))
    assert isinstance(transcribed_on, datetime.date)  # guaranteed by the check above
    return ManualRecord(
        document_ref=f"{stem}.pdf", dish_name_th=str(dish), province_th=str(province),
        district_th=district,
        dish_category_source=category_src if isinstance(category_src, str) else None,
        dish_category=DISH_CATEGORIES.get(str(category_src)) if category_src else None,
        occasion_th=occasion_th if isinstance(occasion_th, str) else None,
        occasion=OCCASIONS.get(str(occasion_th)) if occasion_th else None,
        endangerment=level if isinstance(level, str) else None,
        transcribed_on=transcribed_on.isoformat(),
        ingredients=ingredients, notes=notes,
    )


def read_manual(path: Path) -> ManualRecord:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ManualError(f"{path.stem}: not valid TOML — {e}") from e
    return parse_manual(path.stem, data)


def manual_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.glob("*.toml") if not p.name.startswith("_"))
