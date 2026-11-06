-- 029  HD-27 amended 2026-11-06: a sixteenth ingredient category, `seasoning`;
--      and ingredient_exclusions, raw strings the researcher decided are not
--      flavour ingredients.
--
-- `seasoning` reverses HD-27's rejected option C at the researcher's instruction
-- (docs/decisions.md, HD-27 amendment). Migration 023 is not edited; its CHECK is
-- replaced here with the same list plus `seasoning`.
--
-- ingredient_exclusions is written only by scripts/load_lexicon.py from the
-- researcher's data/reference/lexicon/ingredient_exclusions.csv (rule 4: the file is
-- the approval). An excluded string maps to no entry; the coverage report counts it
-- apart from "unmapped".

ALTER TABLE canonical_ingredients DROP CONSTRAINT canonical_ingredients_category_check;

ALTER TABLE canonical_ingredients
  ADD CONSTRAINT canonical_ingredients_category_check
  CHECK (category IN (
    'aromatic', 'chilli', 'herb', 'spice', 'vegetable', 'fruit',
    'protein_meat', 'protein_fish', 'protein_other', 'coconut', 'acid', 'fat',
    'starch', 'sweetener',
    'seasoning',      -- HD-27 amendment 2026-11-06: sauces, salt, MSG, seasoning powders
    'other'           -- kept under 5% of the lexicon (enforced by the loader)
  ));

CREATE TABLE ingredient_exclusions (
  alias             TEXT PRIMARY KEY,
  reason            TEXT,
  approved_by_human BOOLEAN NOT NULL DEFAULT true
);
