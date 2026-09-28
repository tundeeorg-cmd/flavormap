-- 023  HD-27 (decided 2026-09-28): the ingredient category taxonomy and the
--      fermentation axis.
--
-- Fifteen categories, one per canonical ingredient, assigned by culinary role rather
-- than botany. Fermentation is deliberately NOT a category: it is its own boolean, so
-- the base ingredient (ปลาร้า → protein_fish) and the process stay measurable
-- independently. Reasons and rejected alternatives: docs/decisions.md, HD-27.
--
-- is_fermented is NOT NULL with no default. A default of false would silently record
-- "not fermented" for every entry nobody looked at. canonical_ingredients is empty when
-- this runs, so no backfill is needed. Changing the category list means a new
-- migration, never an edit to this one.

ALTER TABLE canonical_ingredients ADD COLUMN is_fermented BOOLEAN NOT NULL;

ALTER TABLE canonical_ingredients
  ADD CONSTRAINT canonical_ingredients_category_check
  CHECK (category IN (
    'aromatic',       -- e.g. kaffir lime leaf, lemongrass: role, not botany
    'chilli',
    'herb',
    'spice',
    'vegetable',
    'fruit',
    'protein_meat',
    'protein_fish',
    'protein_other',
    'coconut',        -- not under fat: coconut cream is a regional divider
    'acid',           -- not under a seasoning bin: sour is a primary flavour axis
    'fat',
    'starch',
    'sweetener',
    'other'           -- kept under 5% of the lexicon (enforced by the loader)
  ));

COMMENT ON COLUMN canonical_ingredients.is_fermented IS
  'HD-27. Fermentation as an axis independent of category. Required, no default.';
