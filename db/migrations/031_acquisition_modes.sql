-- 031  Acquisition modes, HD-15 (decided 2026-11-06: C, hand-coded; every mode stored;
-- place-only text = 'local').
--
-- recipe_ingredients.acquisition_modes: every mode the source's ที่มา text names, from
-- the researcher's coding file only (scripts/acquisition.py). NULL = not coded, or
-- coded as naming no source. Never inferred by a parser.
--
-- recipe_ingredients.acquisition_mode (005, single value) is retired: HD-15 rejected a
-- single mode per row. It has never held a value; the CHECK keeps it that way.
--
-- acquisition_map: the researcher's coding, loaded whole from the gitignored
-- data/reference/acquisition_map.csv (DCP-derived strings, some with district detail;
-- HD-3, HD-21). The database is never released; release builders must not export it.

ALTER TABLE recipe_ingredients ADD COLUMN acquisition_modes TEXT[]
  CHECK (acquisition_modes IS NULL OR (
    cardinality(acquisition_modes) > 0
    AND acquisition_modes <@ ARRAY['grown','foraged','market','packaged','local']::TEXT[]));
ALTER TABLE recipe_ingredients ADD CONSTRAINT recipe_ingredients_acquisition_mode_retired
  CHECK (acquisition_mode IS NULL);

CREATE TABLE acquisition_map (
  acquisition_raw TEXT PRIMARY KEY,         -- whitespace-collapsed ที่มา text, as parsed
  modes           TEXT[] CHECK (modes IS NULL OR (
                    cardinality(modes) > 0
                    AND modes <@ ARRAY['grown','foraged','market','packaged','local']::TEXT[])),
  loaded_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE acquisition_map IS
  'HD-15: the researcher''s ที่มา coding; modes NULL = coded as naming no source. Uncoded strings are absent.';
COMMENT ON COLUMN recipe_ingredients.acquisition_modes IS
  'HD-15: every mode the ที่มา text names (grown|foraged|market|packaged|local); NULL = uncoded or none.';
