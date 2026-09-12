-- 015  recipes.register — official | commercial | domestic (Bible v4 §3, §4 RQ1).
--
-- The three-way distinction RQ1 compares: what the state selected (official, e.g.
-- dcp_food), what a commercial recipe site publishes (commercial, e.g. kapook_cooking),
-- and what a fieldwork informant actually cooks (domestic, e.g. the Nan/Surin
-- interviews). This is not `sources.source_type` (institutional | web_scraped |
-- interview | cookbook, a property of the *source*) — register is the Bible's own
-- vocabulary for the analytical axis RQ1 and Figure 1/6 run on, and it does not exist
-- under any name in the schema before this migration.
--
-- Added now, before any row exists in `recipes`, because CLAUDE.md §3 calls it "the
-- single most important column in v4" and says explicitly that it "must not be
-- retrofitted" — a column added after real rows exist would need every prior load
-- back-filled from source metadata, which is exactly the kind of after-the-fact
-- reconstruction the Bible's raw-immutability rule (rule 1) exists to avoid needing.
--
-- NOT NULL with no default: every future loader must decide this explicitly rather
-- than inherit a silently-guessed value.

ALTER TABLE recipes
  ADD COLUMN register TEXT NOT NULL
    CHECK (register IN ('official', 'commercial', 'domestic'));

CREATE INDEX recipes_register_idx ON recipes (register);

-- v_recipes_clean (012) carries register through, matching the existing rule that
-- source_type must accompany every analysis (limitations L14-L16) — register is the
-- finer-grained axis RQ1 actually compares and deserves the same treatment.
--
-- `register` is appended as the LAST select-list column, not inserted where it
-- conceptually belongs next to dish_category_source: CREATE OR REPLACE VIEW can only
-- add trailing columns to an existing view, never reorder or insert among them.
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
       r.register
FROM recipes r
JOIN province_attribution pa USING (recipe_id)
JOIN raw_recipes rr ON rr.raw_id = r.raw_id
JOIN sources s ON s.source_id = rr.source_id
JOIN recipe_ingredients ri USING (recipe_id)
WHERE pa.confidence IN ('high','medium')
GROUP BY r.recipe_id, r.name_th, r.dish_category_source, r.register,
         pa.province_code, pa.region, pa.confidence, pa.tier,
         s.source_id, s.source_type, rr.published_at
HAVING count(ri.canonical_id) BETWEEN 3 AND 25;
