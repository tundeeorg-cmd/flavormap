-- 028  crop_production — supporting agricultural statistics, not recipe data.
--
-- data/raw/gdcatalog/flavormap_oae_production.csv: crop production statistics from
-- สำนักงานเศรษฐกิจการเกษตร (OAE), 482 rows, 77 provinces, 11 commodities, years 2567/2568.
-- This table answers no research question on its own (docs/decisions.md, 2026-09-12
-- entry) — it is a lexicon cross-reference and interview-prep aid. Separate from
-- `recipes` and `source_catalogue` because it has no ingredient text and no dishes.
--
-- Zero PDPA exposure: confirmed by inspection, no name/address/contact column exists
-- in the source. This is the first source in the project with that property.
--
-- THE UNIT TRAP. production_unit is not uniform: rice, garlic, shallot etc. are in
-- ตัน (tonnes), มะพร้าวผลแก่ (mature coconut) is in ผล (individual fruits).
-- SUM(production) or any rank/comparison across commodity_th values is meaningless
-- unless grouped by production_unit — the totals are not commensurable. No view or
-- rollup is defined on this table for exactly that reason; any query touching
-- `production` must filter to a single commodity_th first.
-- src/ingest/oae_production.py::check_unit_consistency() asserts one unit per
-- commodity at load time so this doesn't drift silently as more years are added.
--
-- Area columns are sparse BY DESIGN, not missing data: which one is populated
-- depends on the commodity's growth habit, never invent a value for the others.
--   planted_area_rai / harvested_area_rai  -- annual crops (rice, garlic, shallot,
--                                              maize, potato, pineapple, onion)
--   standing_area_rai / bearing_area_rai   -- perennials (coffee, coconut, pepper)
--   standing_area_rai / tapped_area_rai    -- rubber only
-- yield_basis records which area the yield_per_rai figure is computed against
-- ('harvested' | 'bearing' | 'tapped') and is carried straight from the source.

CREATE TABLE crop_production (
  id                  BIGSERIAL PRIMARY KEY,

  province_th         TEXT NOT NULL,   -- validated against data/reference/provinces.csv
                                        -- at load time (src/ingest/oae_production.py);
                                        -- not an FK — see source_catalogue's precedent
                                        -- for why province_th stays plain TEXT here.
  region_th           TEXT NOT NULL,   -- confirmed identical vocabulary to
                                        -- flavormap_food67.csv's region_th (six values)
  commodity_th        TEXT NOT NULL,
  subcommodity_th     TEXT NOT NULL,

  year_be             TEXT NOT NULL,   -- Buddhist Era, as given in the source ('2567')
  year_ce             INTEGER NOT NULL,

  planted_area_rai    NUMERIC,
  standing_area_rai   NUMERIC,
  harvested_area_rai  NUMERIC,
  bearing_area_rai    NUMERIC,
  tapped_area_rai     NUMERIC,

  production          NUMERIC,
  production_unit     TEXT NOT NULL,   -- 'ตัน' | 'ผล' — see the unit-trap note above
  yield_per_rai        NUMERIC,
  yield_unit          TEXT NOT NULL,
  yield_basis         TEXT NOT NULL CHECK (yield_basis IN ('harvested', 'bearing', 'tapped')),

  source_dataset       TEXT,           -- OAE's own dataset title for this row, carried
                                        -- through as provenance
  source_file          TEXT NOT NULL,
  row_hash             TEXT NOT NULL UNIQUE,
  collected_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX crop_production_province_idx ON crop_production (province_th);
CREATE INDEX crop_production_commodity_idx ON crop_production (commodity_th, year_be);
