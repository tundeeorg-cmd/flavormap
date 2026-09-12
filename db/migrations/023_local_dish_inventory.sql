-- 023  local_dish_inventory — community/village dish-name surveys (gdcatalog).
--
-- NOT the recipes table, deliberately. This source (per-community, per-village dish
-- NAME lists with zero ingredients) cannot join the ingredient-based analysis
-- v_recipes_clean and friends run on, and loading it into `recipes` would silently
-- promise ingredient coverage this source cannot supply. A dish name here is a
-- distinct fact worth counting on its own (RQ3's official-vs-community arithmetic is
-- a dish COUNT), which is why the grain is one row per (community, dish), not one row
-- per community.
--
-- `raw_id` links every dish row for one community back to a single `raw_recipes` row
-- for that community's CSV record — the same raw/derived separation rule 1 requires
-- everywhere else, applied to a source with no ingredients to separate out.

CREATE TABLE local_dish_inventory (
  dish_id           BIGSERIAL PRIMARY KEY,
  raw_id            BIGINT NOT NULL REFERENCES raw_recipes,

  dish_name         TEXT NOT NULL,

  community         TEXT,          -- ชุมชน/หมู่บ้าน
  moo               TEXT,          -- หมู่ที่
  subdistrict       TEXT,          -- ตำบล
  district          TEXT,          -- อำเภอ

  -- Rule 2: nullable by design. This file carries no province column at all — see
  -- docs/decisions.md's 2026-09-12 note. A NULL here means district-to-province
  -- resolution failed, exactly as rule 2 wants, never a guessed value.
  province_code     TEXT REFERENCES provinces,

  -- Records WHERE province_code came from when it is not NULL. For this source it is
  -- always "inferred from district names, not stated in the source" — the
  -- provenance distinction the brief asks to preserve into the dataset card, because
  -- an inferred province and a source-stated one are not the same claim.
  provenance_note   TEXT,

  register          TEXT NOT NULL CHECK (register IN ('official','commercial','domestic')),

  -- Distinct from both recipes.source_programme values (migration 022) — a third
  -- government programme, same reasoning as that migration: different selection
  -- criteria, never pooled under a bare register value.
  source_programme  TEXT NOT NULL CHECK (source_programme = 'local_food_survey'),

  -- ผลิตภัณฑ์เด่น — mixed food and non-food community products, stored verbatim.
  -- Classifying the two is a decision gate, not this loader's to make.
  featured_products TEXT,

  collected_at      DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE INDEX local_dish_inventory_province_idx ON local_dish_inventory (province_code);
CREATE INDEX local_dish_inventory_raw_id_idx ON local_dish_inventory (raw_id);
