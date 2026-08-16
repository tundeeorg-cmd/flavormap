-- 003  recipes

CREATE TABLE recipes (
  recipe_id       BIGSERIAL PRIMARY KEY,
  raw_id          BIGINT NOT NULL REFERENCES raw_recipes,
  name_th         TEXT NOT NULL,
  name_en         TEXT,

  -- Category EXACTLY as the source stated it — e.g. the DCP form's three-way
  -- อาหารคาว / อาหารหวาน / อาหารว่าง. This is an INPUT to the RQ5 taxonomy and is
  -- never itself the taxonomy (Bible §5 RQ5). The load-bearing dish_category column,
  -- FK to dish_categories, is added by a forward migration after HD-9 signs off the
  -- taxonomy — deliberately not creatable before that gate.
  dish_category_source TEXT,

  occasion        TEXT,        -- ประจำ | เทศกาล | ฤดูกาล | อื่นๆ
  endangerment    TEXT,        -- four-level risk-of-disappearance scale, source-stated
  cooking_methods TEXT[],
  method_text     TEXT,
  collection_date DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE INDEX recipes_raw_id_idx ON recipes (raw_id);
