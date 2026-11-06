-- 032  The state-promotional register (HD-39, decided 2026-11-06: B) and its dish-name
--      list; sources rows for tat_food and m_culture.
--
-- register gains 'state_promotional': TAT and Ministry of Culture provincial-office
-- collections, kept apart from the DCP 'official' register so the balanced 3 x 77
-- design stays intact. Only rows with ingredient text become recipes.
--
-- state_dish_names: rows that only name a dish (HD-39), for RQ3 / RQ5 matching. Never
-- a recipe. listed_province_code is the province the article (TAT) or office
-- (m-culture) lists the dish under, a fact about the listing, not an attribution.
--
-- sources: facts from ETHICS.md's dated rows (researcher's go for both, 2026-10-12).
-- province_quality NULL: per-row attribution is decided separately (TAT 2026-11-06).

ALTER TABLE recipes DROP CONSTRAINT recipes_register_check;
ALTER TABLE recipes ADD CONSTRAINT recipes_register_check
  CHECK (register IN ('official', 'commercial', 'domestic', 'state_promotional'));

INSERT INTO sources (source_id, source_type, base_url, robots_ok, audited_on,
                     est_recipes, province_quality)
VALUES ('tat_food', 'institutional', 'https://thai.tourismthailand.org', true,
        '2026-10-12', 718, NULL),
       ('m_culture', 'institutional', 'https://www.m-culture.go.th', true,
        '2026-10-12', 2584, NULL)
ON CONFLICT (source_id) DO NOTHING;

CREATE TABLE state_dish_names (
  name_id              BIGSERIAL PRIMARY KEY,
  source_id            TEXT NOT NULL REFERENCES sources,
  record_key           TEXT NOT NULL,          -- TAT record_id; m-culture site_id:item_id
  listed_province_code TEXT REFERENCES provinces (province_code),
  dish_name_th         TEXT,
  dish_name_en         TEXT,
  list_kind            TEXT,                   -- TAT's list kind; NULL for m-culture
  duplicate_of         TEXT,                   -- m-culture collector's flag (HD-41: review)
  published_at         DATE,
  source_url           TEXT NOT NULL,
  CHECK (dish_name_th IS NOT NULL OR dish_name_en IS NOT NULL),
  UNIQUE (source_id, record_key)
);
CREATE INDEX state_dish_names_province_idx ON state_dish_names (listed_province_code);

COMMENT ON TABLE state_dish_names IS
  'HD-39: state-promotional rows that name a dish without ingredients. Never recipes.';
