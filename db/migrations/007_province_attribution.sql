-- 007  province_attribution — the four-tier ladder, highest tier wins.
--
-- Rule 2: attribution failure means province_code IS NULL. There is no
-- nearest-neighbour fill and no "probably Central". A row with a NULL province is a
-- legitimate, reportable outcome and feeds the RQ3 unlabelled fraction.

CREATE TABLE province_attribution (
  recipe_id     BIGINT PRIMARY KEY REFERENCES recipes,
  province_code TEXT REFERENCES provinces,  -- nullable by design
  region        TEXT,
  tier          SMALLINT NOT NULL CHECK (tier BETWEEN 1 AND 4),
                  -- 1 = explicit province string
                  -- 2 = region only
                  -- 3 = dish-name lookup
                  -- 4 = LLM inference
  confidence    TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
  method_note   TEXT,
  rationale     TEXT,                       -- model reasoning, kept for audit

  -- Set when a parsed province disagrees with a discovery-time hint (e.g. a URL index).
  -- Task 3b: log both and flag; never silently prefer either.
  conflict_note TEXT
);

CREATE INDEX province_attribution_province_idx ON province_attribution (province_code);
CREATE INDEX province_attribution_tier_idx ON province_attribution (tier, confidence);
