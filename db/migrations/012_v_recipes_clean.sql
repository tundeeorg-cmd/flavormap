-- 012  v_recipes_clean — the analysis view. All analysis reads from here.
--
-- Excludes low-confidence attribution entirely; tier-4-low never enters (rule: it is
-- available for sensitivity analysis only, pulled explicitly by src/analyze/sensitivity.py).
-- source_type is carried so no analysis can silently pool the institutional corpus with
-- web-scraped recipes (limitations L14–L16).

CREATE VIEW v_recipes_clean AS
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
       count(ri.canonical_id) AS n_ingredients
FROM recipes r
JOIN province_attribution pa USING (recipe_id)
JOIN raw_recipes rr ON rr.raw_id = r.raw_id
JOIN sources s ON s.source_id = rr.source_id
JOIN recipe_ingredients ri USING (recipe_id)
WHERE pa.confidence IN ('high','medium')
GROUP BY r.recipe_id, r.name_th, r.dish_category_source,
         pa.province_code, pa.region, pa.confidence, pa.tier,
         s.source_id, s.source_type, rr.published_at
HAVING count(ri.canonical_id) BETWEEN 3 AND 25;
