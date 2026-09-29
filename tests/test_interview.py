"""Fieldwork interview loader: src/ingest/interview.py and scripts/load_interviews.py.

Three levels, as in tests/test_cook_along.py:

1. **Parse**: consent, IDs, provinces, keys, personal data, lengths, dish numbering.
2. **Files on disk**: the template documents every key; any real file is valid.
3. **Database**: what a load writes, update-in-place on reload, the official-dish link
   check, and that nothing personal lands.

Every person-shaped value here is invented, using the surname ทดสอบ ("test"), as in
tests/test_pdpa.py. Database tests use informant INT_BRM_999 and create any reference
row they need (province, official recipe), removing only what they created, so they run
on a fresh database (make verify) as well as the live one.
"""

from __future__ import annotations

import datetime
import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from scripts.load_interviews import INTERVIEWS_DIR, SOURCE_ID, load, read_all
from src.db import get_connection
from src.ingest.interview import (
    DISH_KEYS,
    INFORMANT_KEYS,
    InterviewError,
    interview_files,
    parse_interview,
    read_interview,
)
from src.ingest.pdpa import find_leaks
from tests.test_pdpa import test_no_personal_data_in_any_table as scan_every_table

D = datetime.date


def _valid(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "informant_id": "INT_BRM_001", "province_code": "TH-31", "district": "เมือง",
        "age_bracket": "gt60", "role": "home cook, rice farmer",
        "consent_form": True, "consent_date": D(2026, 11, 1),
        "interview_date": D(2026, 11, 1),
        "dishes": [{
            "dish_no": 1, "name_th": "ยำลูกผึ้ง", "ingredients": ["ลูกผึ้ง", "หอมแดง"],
            "official_recipe_id": 42, "cook_status_verbatim": "เด็กสมัยนี้ไม่ค่อยกินแล้ว",
            "stated_absence": "ไม่ใส่น้ำตาล",
        }],
    }
    base.update(over)
    return base


# ── 1. parse ──────────────────────────────────────────────────────────────────

def test_a_valid_interview_parses() -> None:
    iv = parse_interview("INT_BRM_001", _valid())
    assert iv.informant_id == "INT_BRM_001" and iv.consent_form is True
    [dish] = iv.dishes
    assert iv.dish_key(dish) == "INT_BRM_001/1"
    assert dish.ingredients == ["ลูกผึ้ง", "หอมแดง"]
    assert dish.official_recipe_id == 42
    assert dish.cook_status_level is None  # never inferred from the words (HD-30)


def _refused(data: dict[str, object], message: str, stem: str = "INT_BRM_001") -> None:
    with pytest.raises(InterviewError, match=message):
        parse_interview(stem, data)


@pytest.mark.parametrize("consent", [False, None, "yes", 1])
def test_no_consent_no_load(consent: object) -> None:
    data = _valid(consent_form=consent)
    if consent is None:
        data.pop("consent_form")
    _refused(data, "consent_form must be explicitly true")


def test_consent_after_the_interview_is_refused() -> None:
    _refused(_valid(consent_date=D(2026, 11, 2)), "consent_date is after interview_date")


@pytest.mark.parametrize(
    ("over", "message", "stem"),
    [
        ({"informant_id": "BRM1"}, "must look like INT_BRM_001", "BRM1"),
        ({"informant_id": "INT_NMA_001"}, "ID prefix NMA does not match TH-31", "INT_NMA_001"),
        ({"province_code": "TH-55"}, "HD-32 fieldwork provinces", "INT_BRM_001"),  # Nan: no longer
        ({"province_code": "TH-32"}, "HD-32 fieldwork provinces", "INT_BRM_001"),
        ({}, "file name must match", "INT_BRM_002"),
    ],
)
def test_ids_and_provinces(over: dict[str, object], message: str, stem: str) -> None:
    _refused(_valid(**over), message, stem)


@pytest.mark.parametrize("bad_key", ["name", "phone", "line_id", "address", "gps_lat"])
def test_personal_data_keys_are_refused_by_name(bad_key: str) -> None:
    _refused(_valid(**{bad_key: "x"}), f"key '{bad_key}' looks like personal data")


@pytest.mark.parametrize("district", [None, "", "   "])
def test_district_is_required(district: object) -> None:
    data = _valid(district=district)
    if district is None:
        data.pop("district")
    _refused(data, "district .อำเภอ. is required")


@pytest.mark.parametrize("key", ["subdistrict", "tambon", "ตำบล", "village", "moo"])
def test_nothing_finer_than_district_is_accepted(key: str) -> None:
    """HD-21 (decided B): subdistrict never enters the database, on either stream."""
    _refused(_valid(**{key: "x"}), "finer than district; HD-21")


@pytest.mark.parametrize("mode", ["grown", "foraged", "market", "packaged"])
def test_the_four_acquisition_modes_are_accepted(mode: str) -> None:
    assert parse_interview("INT_BRM_001", _valid(acquisition_mode=mode)).acquisition_mode == mode


@pytest.mark.parametrize("mode", ["shop", "Market", "bought", ""])
def test_any_other_acquisition_mode_is_refused(mode: str) -> None:
    _refused(_valid(acquisition_mode=mode), "acquisition_mode must be one of")


def test_unknown_keys_are_refused() -> None:
    _refused(_valid(age_braket="gt60"), "unknown key 'age_braket'")


@pytest.mark.parametrize(
    "text", ["นางสมหญิง ทดสอบ", "โทร 08 1234 5678", "เลขที่ ๙๙/๙ หมู่ ๖", "a@example.com"],
)
@pytest.mark.parametrize("where", ["role", "district", "ingredient", "stated_absence"])
def test_personal_data_in_any_text_is_refused_and_never_echoed(text: str, where: str) -> None:
    data = _valid()
    dish = dict(data["dishes"][0])  # type: ignore[index]
    if where == "ingredient":
        dish["ingredients"] = ["หอมแดง", text]
    elif where == "stated_absence":
        dish["stated_absence"] = text
    else:
        data[where] = text
    data["dishes"] = [dish]
    with pytest.raises(InterviewError, match="contains personal data") as exc:
        parse_interview("INT_BRM_001", data)
    assert not find_leaks(str(exc.value))


def test_free_text_over_500_characters_is_refused() -> None:
    dish = {**_valid()["dishes"][0], "validation_notes": "ก" * 501}  # type: ignore[index]
    _refused(_valid(dishes=[dish]), "501 characters; the limit is 500")


@pytest.mark.parametrize(
    ("dishes", "message"),
    [
        ([], "at least one"),
        ([{"name_th": "ส้มตำ"}], "dish_no must be a positive integer"),
        ([{"dish_no": 1, "name_th": "ก"}, {"dish_no": 1, "name_th": "ข"}], "used twice"),
        ([{"dish_no": 1}], "name_th is required"),
        ([{"dish_no": 1, "name_th": "ก", "cook_status_level": "rare"}],
         "cook_status_level must be one of"),
        ([{"dish_no": 1, "name_th": "ก", "official_recipe_id": "42"}],
         "official_recipe_id must be an integer"),
    ],
)
def test_dish_rules(dishes: list[dict[str, object]], message: str) -> None:
    _refused(_valid(dishes=dishes), message)


def test_every_problem_is_listed_at_once() -> None:
    with pytest.raises(InterviewError) as exc:
        parse_interview("INT_BRM_001", _valid(consent_form=False, age_bracket="old"))
    assert "consent_form" in str(exc.value) and "age_bracket" in str(exc.value)


def test_dishes_are_ordered_by_their_own_number() -> None:
    iv = parse_interview("INT_BRM_001", _valid(dishes=[
        {"dish_no": 3, "name_th": "ค"}, {"dish_no": 1, "name_th": "ก"},
    ]))
    assert [d.dish_no for d in iv.dishes] == [1, 3]


# ── 2. files on disk ──────────────────────────────────────────────────────────

def test_template_documents_every_key() -> None:
    text = (INTERVIEWS_DIR / "_template.toml").read_text(encoding="utf-8")
    missing = [k for k in sorted(INFORMANT_KEYS | DISH_KEYS) if k != "dishes" and k not in text]
    assert not missing


def test_template_is_skipped_and_real_files_are_valid() -> None:
    assert all(not p.name.startswith("_") for p in interview_files(INTERVIEWS_DIR))
    for path in interview_files(INTERVIEWS_DIR):
        read_interview(path)  # raises on any invalid file
        assert not find_leaks(path.read_text(encoding="utf-8")), path.name


# ── 3. database ───────────────────────────────────────────────────────────────

IID = "INT_BRM_999"
_OFFICIAL_SRC = "_test_interview_official_src"


def _q(sql: str, *params: object) -> list[tuple[object, ...]]:
    conn = get_connection()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


@pytest.fixture
def db_refs() -> Iterator[dict[str, int]]:
    """Buri Ram and Nan provinces (created only if missing), plus one synthetic official
    recipe in each and one commercial recipe."""
    conn = get_connection()
    created = [
        code for code, th, en, region, lat, lon in (
            ("TH-31", "บุรีรัมย์", "Buri Ram", "Northeast", 14.99, 103.1),
            ("TH-55", "น่าน", "Nan", "North", 18.8, 100.8),
        )
        if conn.execute(
            """INSERT INTO provinces (province_code, name_th, name_en, region4,
                                     centroid_lat, centroid_lon)
               VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING 1""",
            (code, th, en, region, lat, lon),
        ).fetchone()
    ]
    conn.execute(
        """INSERT INTO sources (source_id, source_type, base_url, robots_ok, audited_on)
           VALUES (%s, 'institutional', 'https://example.com', true, '2026-09-29')""",
        (_OFFICIAL_SRC,),
    )
    ids: dict[str, int] = {}
    for label, register, province in (("brm", "official", "TH-31"),
                                      ("nan", "official", "TH-55"),
                                      ("com", "commercial", None)):
        raw = conn.execute(
            """INSERT INTO raw_recipes (source_id, source_url, raw_path, content_hash)
               VALUES (%s, %s, '/tmp/_t', %s) RETURNING raw_id""",
            (_OFFICIAL_SRC, f"x/{label}", f"h-{label}"),
        ).fetchone()[0]  # type: ignore[index]
        rid = conn.execute(
            "INSERT INTO recipes (raw_id, name_th, register) VALUES (%s, 'ทดสอบ', %s) "
            "RETURNING recipe_id", (raw, register),
        ).fetchone()[0]  # type: ignore[index]
        if province:
            conn.execute(
                """INSERT INTO province_attribution (recipe_id, province_code, tier,
                       confidence, method_note) VALUES (%s, %s, 1, 'high', 'test')""",
                (rid, province),
            )
        ids[label] = int(rid)
    conn.commit()
    try:
        yield ids
    finally:
        conn.rollback()
        conn.execute("DELETE FROM interview_dishes WHERE informant_id = %s", (IID,))
        conn.execute(
            """DELETE FROM province_attribution WHERE recipe_id IN (
                   SELECT r.recipe_id FROM recipes r JOIN raw_recipes rr USING (raw_id)
                    WHERE rr.source_id = %s AND rr.source_url LIKE %s
                   UNION SELECT unnest(%s::bigint[]))""",
            (SOURCE_ID, f"interview:{IID}/%", list(ids.values())),
        )
        conn.execute(
            """DELETE FROM recipes WHERE raw_id IN (SELECT raw_id FROM raw_recipes
                WHERE (source_id = %s AND source_url LIKE %s) OR source_id = %s)""",
            (SOURCE_ID, f"interview:{IID}/%", _OFFICIAL_SRC),
        )
        conn.execute(
            "DELETE FROM raw_recipes WHERE (source_id = %s AND source_url LIKE %s) "
            "OR source_id = %s", (SOURCE_ID, f"interview:{IID}/%", _OFFICIAL_SRC),
        )
        conn.execute("DELETE FROM sources WHERE source_id = %s", (_OFFICIAL_SRC,))
        conn.execute("DELETE FROM informants WHERE informant_id = %s", (IID,))
        for code in created:
            conn.execute("DELETE FROM provinces WHERE province_code = %s", (code,))
        conn.commit()
        conn.close()


def _interview(official: int | None, **dish_over: object) -> list:  # type: ignore[type-arg]
    dish = {"dish_no": 1, "name_th": "ยำลูกผึ้ง", "ingredients": ["ลูกผึ้ง", "หอมแดง"],
            "cook_status_verbatim": "ไม่ค่อยมีคนทำแล้ว", "stated_absence": "ไม่ใส่น้ำตาล",
            **dish_over}
    if official is not None:
        dish["official_recipe_id"] = official
    return [parse_interview(IID, _valid(informant_id=IID, dishes=[dish]))]


def test_a_load_writes_the_domestic_register_and_the_interview(
    db_refs: dict[str, int], tmp_path: Path
) -> None:
    load(_interview(db_refs["brm"]), tmp_path)
    [(recipe_id, name, register, official, verbatim, level, absence)] = _q(
        """SELECT r.recipe_id, d.dish_name_th, r.register, d.official_recipe_id,
                  d.cook_status_verbatim, d.cook_status_level, d.stated_absence
             FROM interview_dishes d JOIN recipes r USING (recipe_id)
            WHERE d.dish_key = %s""", f"{IID}/1")
    assert (name, register, official) == ("ยำลูกผึ้ง", "domestic", db_refs["brm"])
    assert verbatim == "ไม่ค่อยมีคนทำแล้ว" and level is None and absence == "ไม่ใส่น้ำตาล"
    assert _q("SELECT province_code, tier, confidence FROM province_attribution "
              "WHERE recipe_id = %s", recipe_id) == [("TH-31", 1, "high")]
    [(parsed,)] = _q("SELECT rr.parsed_json FROM recipes r JOIN raw_recipes rr "
                     "USING (raw_id) WHERE r.recipe_id = %s", recipe_id)
    as_dict = parsed if isinstance(parsed, dict) else json.loads(str(parsed))
    assert [i["name_th"] for i in as_dict["ingredients"]] == ["ลูกผึ้ง", "หอมแดง"]
    assert _q("SELECT consent_form FROM informants WHERE informant_id = %s", IID) == [(True,)]


def test_reloading_an_edited_interview_updates_in_place(
    db_refs: dict[str, int], tmp_path: Path
) -> None:
    load(_interview(db_refs["brm"]), tmp_path)
    load(_interview(db_refs["brm"], cook_status_level="near_lost",
                    ingredients=["ลูกผึ้ง", "หอมแดง", "ตะไคร้"]), tmp_path)
    assert _q("SELECT count(*) FROM interview_dishes WHERE informant_id = %s", IID) == [(1,)]
    assert _q("SELECT count(*) FROM raw_recipes WHERE source_url LIKE %s",
              f"interview:{IID}/%") == [(1,)]
    assert _q("SELECT cook_status_level FROM interview_dishes WHERE dish_key = %s",
              f"{IID}/1") == [("near_lost",)]


def test_a_link_to_a_non_official_recipe_aborts_the_whole_load(
    db_refs: dict[str, int], tmp_path: Path
) -> None:
    with pytest.raises(InterviewError, match="is not an official recipe"):
        load(_interview(db_refs["com"]), tmp_path)
    assert _q("SELECT count(*) FROM informants WHERE informant_id = %s", IID) == [(0,)]


def test_a_cross_province_link_loads_and_is_reported(
    db_refs: dict[str, int], tmp_path: Path
) -> None:
    notes = load(_interview(db_refs["nan"]), tmp_path)
    assert notes["cross_province_links"] == [f"{IID}/1 -> recipe {db_refs['nan']} (TH-55)"]


def test_no_link_means_no_official_counterpart(db_refs: dict[str, int], tmp_path: Path) -> None:
    load(_interview(None), tmp_path)
    assert _q("SELECT official_recipe_id FROM interview_dishes WHERE dish_key = %s",
              f"{IID}/1") == [(None,)]


def test_nothing_personal_lands(db_refs: dict[str, int], tmp_path: Path) -> None:
    load(_interview(db_refs["brm"]), tmp_path)
    rows = _q("SELECT i::text FROM informants i WHERE informant_id = %s", IID)
    rows += _q("SELECT d::text FROM interview_dishes d WHERE informant_id = %s", IID)
    for (text,) in rows:
        assert not find_leaks(str(text))


def test_register_is_explicit_domestic_and_never_a_default(
    db_refs: dict[str, int], tmp_path: Path
) -> None:
    """recipes.register has no default (migration 015), and the loader writes
    'domestic' itself, so an interview dish can never inherit a register."""
    assert _q("SELECT column_default, is_nullable FROM information_schema.columns "
              "WHERE table_name = 'recipes' AND column_name = 'register'") == [(None, "NO")]
    load(_interview(db_refs["brm"]), tmp_path)
    assert _q("SELECT r.register FROM interview_dishes d JOIN recipes r USING (recipe_id) "
              "WHERE d.dish_key = %s", f"{IID}/1") == [("domestic",)]


@pytest.mark.parametrize(
    "pii", ["นางสมหญิง ทดสอบ", "โทร 08 1234 5678", "เลขที่ ๙๙/๙ หมู่ ๖", "ถนน ทดสอบ",
            "ทดสอบ@example.com"],
)
@pytest.mark.parametrize("field", ["role", "district", "name_th", "ingredient",
                                   "cook_status_verbatim", "stated_absence",
                                   "validation_notes"])
def test_no_informant_name_address_or_phone_can_reach_any_table(
    db_refs: dict[str, int], tmp_path: Path, pii: str, field: str
) -> None:
    """The dcp_food standard (tests/test_pdpa.py): after any interview load, attempted or
    real, a scan of every text and JSON column of every table finds no personal data."""
    data = _valid(informant_id=IID)
    dish = {"dish_no": 1, "name_th": "ยำลูกผึ้ง", "ingredients": ["ลูกผึ้ง"]}
    if field in ("role", "district"):
        data[field] = pii
    elif field == "ingredient":
        dish["ingredients"] = ["ลูกผึ้ง", pii]
    else:
        dish[field] = pii
    data["dishes"] = [dish]
    path = tmp_path / f"{IID}.toml"
    path.write_text(_to_toml(data), encoding="utf-8")
    with pytest.raises(InterviewError):
        load(read_all(tmp_path), tmp_path)
    assert _q("SELECT count(*) FROM informants WHERE informant_id = %s", IID) == [(0,)]
    load(_interview(db_refs["brm"]), tmp_path / "unused")  # a clean load alongside
    scan_every_table()


def _to_toml(data: dict[str, object]) -> str:
    """Just enough TOML for these fixtures: strings, ints, bools, dates, one dish list."""
    def value(v: object) -> str:
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, datetime.date)):
            return str(v)
        if isinstance(v, list):
            return "[" + ", ".join(value(x) for x in v) + "]"
        return json.dumps(v, ensure_ascii=False)
    lines = [f"{k} = {value(v)}" for k, v in data.items() if k != "dishes"]
    for dish in data.get("dishes", []):  # type: ignore[attr-defined]
        lines.append("[[dishes]]")
        lines += [f"{k} = {value(v)}" for k, v in dish.items()]
    return "\n".join(lines) + "\n"


def test_the_committed_directory_holds_only_the_template() -> None:
    """HD-30: interview files never reach git. Checked against what git tracks."""
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files", "data/interviews"], capture_output=True, text=True, check=True,
        cwd=INTERVIEWS_DIR.parent.parent,
    ).stdout.split()
    assert tracked in ([], ["data/interviews/_template.toml"])
    assert read_all(INTERVIEWS_DIR) is not None
