-- 027  seed sources — mthai_food's registry row (HD-40, decided 2026-11-06).
--
-- scripts/parse_mthai.py --load writes raw_recipes rows, which need this FK row, the
-- same gap 017 and 018 closed for dcp_food and kapook_cooking. Facts from ETHICS.md's
-- dated row (researcher's go, 2026-10-12: ingredient lists only) and the export: 200
-- posts. province_quality is left NULL: per-recipe labels follow HD-37, and no
-- source-level judgment has been made.

INSERT INTO sources (source_id, source_type, base_url, robots_ok, audited_on,
                     est_recipes, province_quality)
VALUES ('mthai_food', 'web_scraped', 'https://mthai.com', true, '2026-10-12', 200, NULL)
ON CONFLICT (source_id) DO NOTHING;
