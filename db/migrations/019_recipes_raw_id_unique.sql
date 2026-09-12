-- 019  recipes.raw_id UNIQUE — closes the re-parse duplication gap.
--
-- Both loaders (scripts/parse_dcp.py, scripts/parse_kapook.py) INSERT INTO recipes with
-- no ON CONFLICT guard, while raw_recipes upserts on (source_id, content_hash). Running
-- either loader twice against the same corpus therefore produced a fresh `recipes` row
-- every time, pointing at the same already-deduplicated raw_id — the row count grew
-- without bound on repeated runs, and it silently defeated parse_dcp.py's own
-- `INSERT INTO province_attribution ... ON CONFLICT (recipe_id) DO NOTHING`, since a
-- conflict on recipe_id could never occur if recipe_id was never stable to begin with.
--
-- The relationship both loaders actually implement is one row in `recipes` per fetched
-- document (DCP: every usable document; kapook: every single-section usable page, per
-- HD-22 option C) — a real 1:1, not a coincidence of how the loaders happen to be
-- written. Replacing the plain index with a UNIQUE constraint makes that relationship
-- enforced rather than assumed, and lets both loaders upsert on it.

DROP INDEX IF EXISTS recipes_raw_id_idx;
ALTER TABLE recipes ADD CONSTRAINT recipes_raw_id_key UNIQUE (raw_id);
