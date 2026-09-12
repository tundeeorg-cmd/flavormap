-- 018  seed sources — kapook_cooking's registry row.
--
-- scripts/parse_kapook.py writes to raw_recipes, which has a NOT NULL FK to sources
-- (001_sources.sql), the same gap 017 closed for dcp_food. Facts transcribed verbatim
-- from ETHICS.md's dated re-audit (2026-08-22) and the fetch record (2026-08-23): 2,702
-- pages fetched, 2,521 yield a machine-readable ingredient list. province_quality is
-- 'none' per the HD-3 kapook decision (2026-08-23) — the labelled fraction measured at
-- 1.3%, and kapook "answers RQ3 well and RQ1 not at all" is the standing decision, not a
-- judgment made here.

INSERT INTO sources (source_id, source_type, base_url, robots_ok, audited_on,
                     est_recipes, province_quality)
VALUES ('kapook_cooking', 'web_scraped', 'https://cooking.kapook.com', true,
        '2026-08-22', 2521, 'none')
ON CONFLICT (source_id) DO NOTHING;
