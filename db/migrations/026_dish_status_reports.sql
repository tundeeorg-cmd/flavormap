-- 026  dish_status_reports — HD-43 (HD-Q10), decided 2026-11-06: option A, verbatim only.
--
-- Q10 is asked about each of the three dishes the state listed for the province,
-- whether or not the cook makes them. These rows never create a `recipes` row, so a
-- dish the cook does not make adds nothing to the domestic register (TIMELINE T1.4).

CREATE TABLE dish_status_reports (
  -- '<informant_id>/q10/<official_recipe_id>': stable, so the loader upserts.
  report_key          TEXT PRIMARY KEY,
  informant_id        TEXT NOT NULL REFERENCES informants,
  -- The state's dish asked about. Entered by the researcher (as HD-30 (1)); the loader
  -- refuses an id that is not register = 'official'.
  official_recipe_id  BIGINT NOT NULL REFERENCES recipes,
  -- Part 2 A: the cook's words, verbatim, each <= 500 characters (loader-enforced).
  -- "Who" is a role (ยาย, แม่ค้า), never a name: the loader's PDPA check refuses names.
  still_made          TEXT,
  who_makes           TEXT,
  young_people_know   TEXT,
  notes               TEXT,
  UNIQUE (informant_id, official_recipe_id)
);

CREATE INDEX dish_status_reports_official_idx ON dish_status_reports (official_recipe_id);
