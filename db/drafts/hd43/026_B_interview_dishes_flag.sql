-- DRAFT, NOT APPLIED. HD-43 (HD-Q10) option B: Q10 answers stay in interview_dishes,
-- flagged when the cook does not make the dish.
-- To adopt: copy to db/migrations/026_interview_dishes_cooked_flag.sql, then
--   git apply db/drafts/hd43/B_loader.patch && make migrate && make test
--
-- A dish with cooked_by_informant = false is a state dish asked about under Q10. The
-- loader writes no raw_recipes, recipes or province_attribution row for it, so it adds
-- nothing to the domestic register (TIMELINE T1.4). Every RQ1/RQ3 query that reads
-- interview_dishes must then filter on the flag.

ALTER TABLE interview_dishes
  -- true for every existing row: until now every dish was one the cook described.
  ADD COLUMN cooked_by_informant BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE interview_dishes
  -- A Q10-only dish has no recipe and must name the state's dish it is about.
  ADD CONSTRAINT interview_dishes_q10_only_shape CHECK (
    cooked_by_informant OR (recipe_id IS NULL AND official_recipe_id IS NOT NULL)
  );

-- Part 2 A: the Q10 answer goes in the existing cook_status_verbatim column.
-- Part 2 B (coded at write-up) would add, e.g.:
--   ALTER TABLE interview_dishes
--     ADD COLUMN still_made_code TEXT CHECK (still_made_code IN ('yes', 'no', 'unsure')),
--     ADD COLUMN young_people_know_code TEXT CHECK (young_people_know_code IN ('yes', 'no', 'unsure'));
