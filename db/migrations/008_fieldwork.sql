-- 008  Fieldwork (Bible §8). Rule 8: no names, no contact details, ever, in any table.

CREATE TABLE informants (
  informant_id   TEXT PRIMARY KEY,          -- 'INT_SRN_001'
  province_code  TEXT NOT NULL REFERENCES provinces,

  -- Sub-provincial resolution costs nothing to record and Isaan provinces are large
  -- (Bible §8). District only — never subdistrict-plus-address.
  district       TEXT,

  -- The cook's predominant sourcing pattern. Per-ingredient acquisition lives on
  -- recipe_ingredients; this is the informant-level summary Bible §8 asks for.
  acquisition_mode TEXT CHECK (acquisition_mode IN ('grown','foraged','market','packaged')),

  age_bracket    TEXT CHECK (age_bracket IN ('lt40','40_60','gt60')),
  role           TEXT,                      -- how they are described in the paper
  consent_form   BOOLEAN NOT NULL,
  consent_date   DATE NOT NULL,
  interview_date DATE NOT NULL
);

CREATE TABLE interview_dishes (
  dish_id               BIGSERIAL PRIMARY KEY,
  informant_id          TEXT NOT NULL REFERENCES informants,
  recipe_id             BIGINT REFERENCES recipes,
  distinctiveness_claim TEXT,   -- what the cook says makes it provincial (Q4)
  stated_absence        TEXT,   -- Q9 — what they would never put in. RQ2 validates here
  differs_from_bangkok  TEXT,
  validation_notes      TEXT    -- their reaction to scraped recipes from their province
);
