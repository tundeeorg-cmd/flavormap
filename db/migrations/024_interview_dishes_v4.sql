-- 024  interview_dishes for Bible v4 — HD-30 (decided 2026-09-29).
--
-- Migration 008 predates v4, whose RQ3 and RQ5 ask two things of an interview it has no
-- columns for. Added here, with a stable key so the loader upserts rather than
-- duplicates. interview_dishes and informants are empty when this runs, so NOT NULL
-- columns need no backfill.

ALTER TABLE interview_dishes
  -- '<informant_id>/<dish_no>', e.g. 'INT_BRM_001/2'. The researcher numbers dishes in
  -- the interview file, so reordering the file cannot re-key a dish.
  ADD COLUMN dish_key TEXT NOT NULL,
  -- The dish as the cook named it. RQ3's table lists these verbatim.
  ADD COLUMN dish_name_th TEXT NOT NULL,
  -- HD-30 (1): the official dish this one corresponds to, entered by the researcher.
  -- NULL means "no official counterpart", which is RQ3's "neither" finding, not missing
  -- data. Never set by name matching.
  ADD COLUMN official_recipe_id BIGINT REFERENCES recipes,
  -- HD-30 (2): the cook's own view of whether the dish is disappearing, word for word,
  -- and a level on the state's scale coded later under HD-11. The level is never
  -- inferred from the words.
  ADD COLUMN cook_status_verbatim TEXT,
  ADD COLUMN cook_status_level TEXT
    CHECK (cook_status_level IN ('lost', 'near_lost', 'transmitted')),
  -- What the cook said they substitute. Listed in the fieldwork.csv release (§12).
  ADD COLUMN stated_substitutions TEXT;

ALTER TABLE interview_dishes
  ADD CONSTRAINT interview_dishes_dish_key_key UNIQUE (dish_key);

CREATE INDEX interview_dishes_official_recipe_idx ON interview_dishes (official_recipe_id);

-- The source every interview-derived raw_recipes row points at. robots_ok and audited_on
-- are NOT NULL on sources: robots_ok is true because no crawling is involved, and
-- audited_on is the date the interview loader and its consent rules were fixed (HD-30).
-- The ethics protocol itself (consent form, chaperone, reciprocity) is in ETHICS.md.
INSERT INTO sources (source_id, source_type, base_url, robots_ok, audited_on,
                     est_recipes, province_quality)
VALUES ('fieldwork_interviews', 'interview', NULL, true, '2026-09-29', 60, 'explicit')
ON CONFLICT (source_id) DO NOTHING;
