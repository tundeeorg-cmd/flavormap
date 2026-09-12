-- 017  seed sources — dcp_food's registry row.
--
-- scripts/parse_dcp.py writes to raw_recipes, which has a NOT NULL FK to sources
-- (001_sources.sql). No migration has ever inserted that row, so `make ingest` on a
-- fresh clone fails on the FK the first time parse_dcp.py runs. Facts below are
-- transcribed verbatim from ETHICS.md's dated source-audit table (audited 2026-08-16),
-- not new judgment calls.
--
-- ON CONFLICT DO NOTHING: idempotent against a database where this row was already
-- inserted by hand (as this one was, once, before this migration existed).

INSERT INTO sources (source_id, source_type, base_url, robots_ok, audited_on,
                     est_recipes, province_quality)
VALUES ('dcp_food', 'institutional', 'https://food.culture.go.th', true, '2026-08-16',
        231, 'explicit')
ON CONFLICT (source_id) DO NOTHING;
