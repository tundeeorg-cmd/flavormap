-- 009  dish_categories — the RQ5 taxonomy.
--
-- SEEDED EMPTY, DELIBERATELY. Bible §5 RQ5 requires "a documented taxonomy of five or
-- six categories and written inclusion rules". Both are HD-9 and neither exists yet.
-- An empty table is the correct state: it makes the gate visible instead of letting a
-- placeholder taxonomy quietly become the real one.
--
-- Source-stated categories (the DCP form's คาว/หวาน/ว่าง) land in
-- recipes.dish_category_source and are an INPUT to this taxonomy, never the taxonomy.

CREATE TABLE dish_categories (
  category_id     TEXT PRIMARY KEY,         -- 'nam_prik', 'curry', …
  name_th         TEXT NOT NULL,
  name_en         TEXT NOT NULL,

  -- Written inclusion rules. NOT NULL because a category without stated boundaries is
  -- not reproducible, and Bible §14 (L10) commits to publishing these so others can
  -- disagree with specific assignments.
  inclusion_rules TEXT NOT NULL,
  exclusion_notes TEXT,
  sort_order      INTEGER NOT NULL,
  decided_at      DATE,                     -- when HD-9 fixed this category
  decision_note   TEXT
);

-- No seed rows. See HD-9 in docs/decisions.md.
