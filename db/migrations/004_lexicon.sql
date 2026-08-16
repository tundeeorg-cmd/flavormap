-- 004  The controlled vocabulary — the project's most defensible contribution
--      (Bible §7). Nothing here is populated automatically.

CREATE TABLE canonical_ingredients (
  canonical_id      TEXT PRIMARY KEY,       -- 'ING_0047'
  name_th           TEXT NOT NULL,
  name_en           TEXT NOT NULL,          -- English gloss: required, opens the lexicon
                                            -- to non-Thai readers (Bible §16)
  category          TEXT NOT NULL,
  regional_note     TEXT,
  approved_by_human BOOLEAN NOT NULL DEFAULT false,
  decision_note     TEXT                    -- why this boundary was drawn (an [HD] gate)
);

-- Approved mappings only. Rule 4: automated similarity NEVER writes here.
CREATE TABLE ingredient_aliases (
  alias             TEXT PRIMARY KEY,
  canonical_id      TEXT NOT NULL REFERENCES canonical_ingredients,
  match_method      TEXT NOT NULL,          -- manual | exact | normalised | embedding | llm
  match_score       REAL,
  approved_by_human BOOLEAN NOT NULL DEFAULT false
);

-- The review queue. Every automated suggestion lands here and waits for a human.
CREATE TABLE alias_candidates (
  candidate_id   BIGSERIAL PRIMARY KEY,
  alias          TEXT NOT NULL,
  canonical_id   TEXT NOT NULL REFERENCES canonical_ingredients,
  match_method   TEXT NOT NULL,             -- normalised | embedding | llm
  match_score    REAL,
  observed_count INTEGER NOT NULL DEFAULT 0, -- frequency, so review is ordered by impact
  status         TEXT NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending','accepted','rejected')),
  reviewed_at    TIMESTAMPTZ,
  review_note    TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX alias_candidates_pair_idx ON alias_candidates (alias, canonical_id);
CREATE INDEX alias_candidates_status_idx ON alias_candidates (status, observed_count DESC);

-- The NOT_same_as guard: pairs a human has ruled must never be merged.
CREATE TABLE ingredient_conflations (
  canonical_id_a TEXT NOT NULL REFERENCES canonical_ingredients,
  canonical_id_b TEXT NOT NULL REFERENCES canonical_ingredients,
  reason         TEXT NOT NULL,
  PRIMARY KEY (canonical_id_a, canonical_id_b)
);
