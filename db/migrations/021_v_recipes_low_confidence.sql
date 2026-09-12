-- 021  v_recipes_low_confidence — the explicit sensitivity-analysis pull.
--
-- CLAUDE.md §3.2: "All analysis reads v_recipes_clean: attribution confidence in
-- (high, medium), 3-25 mapped ingredients. Low-confidence rows exist for sensitivity
-- analysis only and are pulled explicitly by src/analyze/sensitivity.py. Tier-4-low
-- never enters the view."
--
-- Same shape as v_recipes_clean (012, extended by 015), confidence flipped: this view
-- is exactly the rows v_recipes_clean's confidence filter excludes. Tier-4-low rows
-- are deliberately INCLUDED here — the rule above is that they never enter
-- v_recipes_clean, not that they are invisible everywhere. They are exactly the kind
-- of row a sensitivity comparison exists to examine.
--
-- The ingredient-count bound (3-25) is kept the same as v_recipes_clean rather than
-- relaxed. It is a separate data-quality axis from attribution confidence, and a
-- sensitivity check on confidence should not be confounded by also changing that one.
--
-- The two views intentionally duplicate their join structure — Postgres views cannot
-- parameterise a WHERE clause — kept in sync by hand. Any schema change touching
-- v_recipes_clean's joins should touch this one too.
--
-- Note for the researcher: recipe_ingredients is empty until HD-6 (canonical
-- ingredients) is decided, and both this view and v_recipes_clean INNER JOIN it. Until
-- then this view returns zero rows regardless of how much data is loaded — the same
-- constraint v_recipes_clean already has, not a new one.

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
       r.register
FROM recipes r
JOIN province_attribution pa USING (recipe_id)
JOIN raw_recipes rr ON rr.raw_id = r.raw_id
JOIN sources s ON s.source_id = rr.source_id
JOIN recipe_ingredients ri USING (recipe_id)
WHERE pa.confidence = 'low'
GROUP BY r.recipe_id, r.name_th, r.dish_category_source, r.register,
         pa.province_code, pa.region, pa.confidence, pa.tier,
         s.source_id, s.source_type, rr.published_at
HAVING count(ri.canonical_id) BETWEEN 3 AND 25;
