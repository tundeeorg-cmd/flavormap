-- 024  recipes: food67/food68 provenance columns, prose fields, and a corrected
-- source_programme vocabulary.
--
-- Three things bundled because they are one forward migration, not because they are
-- one idea:

-- (1) Provenance columns `flavormap_food67.csv` carries per dish that no other
-- loaded source has needed: a source-assigned dish id, and page references into the
-- shared book PDF each row cites (`book_page` = the book's own printed page number,
-- `pdf_pages` = the underlying PDF's page reference — not assumed to be the same
-- number, and not assumed to be a single integer, hence TEXT). `raw_recipes.source_url`
-- (002) already carries the per-document fetch URL for every other source; this file
-- gives a *per-row* URL (a `#p=N` fragment into one shared book), which is what
-- `raw_recipes.source_url` already models — no new column needed there.
ALTER TABLE recipes
  ADD COLUMN source_dish_id TEXT,
  ADD COLUMN book_page      TEXT,
  ADD COLUMN pdf_pages      TEXT;

-- (2) Prose fields the Bible's rule (ingredient lists and labels only, never recipe
-- prose) forbids publishing but that RQ4's cook-alongs need locally. `source_info_th`
-- additionally needs a PDPA pass before it is ever written — see
-- src/ingest/food67.py and tests/test_food67_pdpa.py; this migration only creates
-- the column, it does not certify what will be stored there.
ALTER TABLE recipes
  ADD COLUMN method_th         TEXT,
  ADD COLUMN method_step_count INTEGER,
  ADD COLUMN benefits_th       TEXT,
  ADD COLUMN history_th        TEXT,
  ADD COLUMN source_info_th    TEXT;

COMMENT ON COLUMN recipes.method_th IS
  'Substantial government-publication prose. Never enters the released dataset — '
  'Bible rule: ingredient lists and labels only. Local-database-only, for RQ4.';
COMMENT ON COLUMN recipes.history_th IS
  'Same restriction as method_th: local-database-only, never released.';
COMMENT ON COLUMN recipes.benefits_th IS
  'Same restriction as method_th: local-database-only, never released.';
COMMENT ON COLUMN recipes.source_info_th IS
  'Free-text source attribution from the publication. Must pass a PDPA redaction '
  'pass before being written (src/ingest/pdpa.py) — this column existing is not '
  'itself a guarantee that happened for any given row. Never released.';

-- (3) source_programme vocabulary correction. Migration 022 added exactly one
-- official-register programme value, 'one_province_one_menu', written by
-- scripts/parse_dcp.py for the food68 (2568) corpus — the only official loader that
-- had ever run. That name carried no year because, at the time, there was only one
-- year. It is renamed here to 'one_province_one_menu_2568' and a distinct
-- 'one_province_one_menu_2567' value is added for this migration's own source
-- (scripts/parse_food67.py), per the brief's explicit instruction: "The 2568 load
-- must be tagged separately." Leaving the old bare name standing for 2568 while
-- adding a year-suffixed name for 2567 only would read as an oversight the next time
-- someone has to explain why one of two sibling values has a year and the other
-- doesn't — corrected now, while only one row's worth of real data is affected.
ALTER TABLE recipes DROP CONSTRAINT recipes_source_programme_check;
ALTER TABLE recipes
  ADD CONSTRAINT recipes_source_programme_check
    CHECK (source_programme IN
      ('one_province_one_menu_2567', 'one_province_one_menu_2568', 'thai_taste_therapy'));

UPDATE recipes SET source_programme = 'one_province_one_menu_2568'
 WHERE source_programme = 'one_province_one_menu';

-- programme_year, explicitly requested (Task 1b) alongside the source_programme
-- rename above — redundant with the year already encoded in source_programme, kept
-- anyway because the brief asks for both and a plain integer year is easier to filter
-- and aggregate on than parsing a suffix out of a programme-name string every time.
-- พ.ศ. (Buddhist Era), matching "food67"/"food68"'s own naming — NOT a Gregorian year.
ALTER TABLE recipes ADD COLUMN programme_year SMALLINT;
UPDATE recipes SET programme_year = 2568 WHERE source_programme = 'one_province_one_menu_2568';

COMMENT ON COLUMN recipes.programme_year IS
  'Buddhist Era (พ.ศ.), matching the source''s own "food67"/"food68" naming — e.g. '
  '2567, not the Gregorian 2024. Redundant with the year suffix on source_programme '
  'by request (Task 1b); kept as a real integer column for filtering/aggregation.';

-- v_recipes_clean and v_recipes_low_confidence are untouched by this migration: none
-- of the columns added here are in their SELECT lists, and neither is source_programme
-- itself expected to be read differently by them now that its vocabulary has two
-- '_2567'/'_2568' values instead of one bare one — every existing predicate and join
-- in both views is unaffected.
