-- 022  recipes.source_programme — distinguishes government programmes within the
-- 'official' register (Bible v4 §3, RQ1).
--
-- `register = 'official'` says the state selected this dish. It does not say which
-- state programme selected it, and as of this migration two exist in the schema with
-- different selection criteria: the 231-document one-province-one-menu PDFs
-- (`dcp_food`, scripts/parse_dcp.py) and `culture.gdcatalog.go.th`'s
-- `thaitastetherapy.csv` (Ministry of Culture open-data catalogue). Pooling them into
-- one undifferentiated "official" bucket would hide that difference from RQ1, which
-- is exactly the kind of source-conflation rule 015's own docstring and CLAUDE.md
-- §3.2 already forbid for source_type — this is the same rule one level down, inside
-- a single register.
--
-- Nullable, not NOT NULL: `commercial` and `domestic` rows have no government
-- programme at all, so the column must be able to say so. The CHECK below ties the
-- two facts together explicitly rather than leaving "official but no programme" or
-- "commercial but tagged with a programme" as states nobody rules out.
--
-- Backfill, not a fresh load: `scripts/parse_dcp.py` already writes register='official'
-- rows and this column did not exist when it ran. Every existing official row is the
-- one-province-one-menu programme by construction — it is the only official loader
-- that has ever written to `recipes` — so backfilling it here is a fact about what was
-- already loaded, not a guess.

ALTER TABLE recipes
  ADD COLUMN source_programme TEXT
    CHECK (source_programme IN ('one_province_one_menu', 'thai_taste_therapy'));

ALTER TABLE recipes
  ADD CONSTRAINT recipes_official_has_programme
    CHECK ((register = 'official') = (source_programme IS NOT NULL));

UPDATE recipes SET source_programme = 'one_province_one_menu' WHERE register = 'official';

-- Carried through v_recipes_clean for the same reason 015 carried `register` through:
-- RQ1 must be able to tell the two official programmes apart without a join back to
-- `recipes`. Appended as the trailing column again — CREATE OR REPLACE VIEW can only
-- add trailing columns, never reorder or insert among the existing ones.
CREATE OR REPLACE VIEW v_recipes_clean AS
SELECT r.recipe_id,
       r.name_th,
       r.dish_category_source,
       pa.province_code,
       pa.region,
       pa.confidence,
       pa.tier,
       s.source_id,
       s.source_type,
       rr.published_at,
       count(ri.canonical_id) AS n_ingredients,
       r.register,
       r.source_programme
FROM recipes r
JOIN province_attribution pa USING (recipe_id)
JOIN raw_recipes rr ON rr.raw_id = r.raw_id
JOIN sources s ON s.source_id = rr.source_id
JOIN recipe_ingredients ri USING (recipe_id)
WHERE pa.confidence IN ('high','medium')
GROUP BY r.recipe_id, r.name_th, r.dish_category_source, r.register, r.source_programme,
         pa.province_code, pa.region, pa.confidence, pa.tier,
         s.source_id, s.source_type, rr.published_at
HAVING count(ri.canonical_id) BETWEEN 3 AND 25;

-- 021's own comment says its join structure duplicates v_recipes_clean's "kept in
-- sync by hand. Any schema change touching v_recipes_clean's joins should touch this
-- one too." CREATE OR REPLACE VIEW cannot be used here — 021 created it as a plain
-- CREATE VIEW — so it is dropped and recreated instead, same trailing-column rule.
DROP VIEW v_recipes_low_confidence;

CREATE VIEW v_recipes_low_confidence AS
SELECT r.recipe_id,
       r.name_th,
       r.dish_category_source,
       pa.province_code,
       pa.region,
       pa.confidence,
       pa.tier,
       s.source_id,
       s.source_type,
       rr.published_at,
       count(ri.canonical_id) AS n_ingredients,
       r.register,
       r.source_programme
FROM recipes r
JOIN province_attribution pa USING (recipe_id)
JOIN raw_recipes rr ON rr.raw_id = r.raw_id
JOIN sources s ON s.source_id = rr.source_id
JOIN recipe_ingredients ri USING (recipe_id)
WHERE pa.confidence = 'low'
GROUP BY r.recipe_id, r.name_th, r.dish_category_source, r.register, r.source_programme,
         pa.province_code, pa.region, pa.confidence, pa.tier,
         s.source_id, s.source_type, rr.published_at
HAVING count(ri.canonical_id) BETWEEN 3 AND 25;
