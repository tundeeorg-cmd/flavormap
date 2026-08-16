-- 005  recipe_ingredients

CREATE TABLE recipe_ingredients (
  recipe_id         BIGINT NOT NULL REFERENCES recipes,
  canonical_id      TEXT NOT NULL REFERENCES canonical_ingredients,
  raw_text          TEXT NOT NULL,          -- exactly as it appeared
  quantity_g        REAL,                   -- rule 3: NULL unless genuinely convertible.
                                            -- ตามชอบ is NULL, never a guessed number.
  has_quantity      BOOLEAN NOT NULL DEFAULT false,

  -- Acquisition, per ingredient (Bible §8; DCP form §4 column ที่มา).
  -- acquisition_raw holds the source's free text verbatim; acquisition_mode holds the
  -- mapped value and stays NULL until HD-15 fixes the mapping.
  acquisition_raw   TEXT,
  acquisition_mode  TEXT CHECK (acquisition_mode IN ('grown','foraged','market','packaged')),

  extraction_method TEXT NOT NULL,          -- llm | rule | interview | institutional_pdf
  human_validated   BOOLEAN NOT NULL DEFAULT false,
  PRIMARY KEY (recipe_id, canonical_id)
);

CREATE INDEX recipe_ingredients_canonical_idx ON recipe_ingredients (canonical_id);
