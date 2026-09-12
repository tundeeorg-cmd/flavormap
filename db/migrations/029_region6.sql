-- 029  provinces.region6 — HD-23's decided canonicalisation target.
--
-- HD-23 (docs/decisions.md, decided 2026-09-12): every source states region
-- differently (food67 six-way, thaitastetherapy four-way with Central+East merged,
-- Wongnai reportedly three-way) and none of them is trusted directly. The canonical
-- region value is derived from `province` only, at six-way granularity — matching
-- food67, the only source that actually draws this resolution.
--
-- Source-stated region strings are NOT deleted or replaced by this migration; they
-- remain in raw_recipes.parsed_json per source, available as a data-quality
-- cross-check, never load-bearing. province_attribution.region (migration 007) is
-- NOT backfilled from this column — storing a derived value there would duplicate
-- what a join through province_code already gives for free, and re-introduce the
-- sync hazard this decision exists to avoid. It stays unpopulated; whether to drop
-- it is a separate, smaller call for later.
--
-- Nullable, like dialect_group (013), for the same reason: an unassigned province is
-- honest, a wrongly-assigned one is not. Every one of the 77 provinces does hold a
-- value as of this migration, but with two different provenances that decisions.md
-- documents explicitly — 48 read directly from flavormap_food67.csv's own region_th
-- column, 29 filled from general Thai administrative geography this session
-- (unverified against a live source, network access blocked throughout). Nothing
-- about the CHECK constraint or the NOT NULL-ness distinguishes the two; the
-- provenance split is recorded in docs/decisions.md, not in the schema.

ALTER TABLE provinces ADD COLUMN region6 TEXT
  CHECK (region6 IN (
    'ภาคกลาง', 'ภาคตะวันตก', 'ภาคตะวันออก',
    'ภาคตะวันออกเฉียงเหนือ', 'ภาคเหนือ', 'ภาคใต้'
  ));

CREATE INDEX provinces_region6_idx ON provinces (region6);
