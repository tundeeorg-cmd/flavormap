-- 028  ingredient_alias_splits — HD-6 question 5 (decided 2026-11-06, "split all").
--
-- A raw string that names several ingredients or alternatives ("ปลาร้าหรือปลาเค็ม",
-- "กะทิ+เครื่องแกง+สับปะรด") becomes one mention per named entry. ingredient_aliases
-- keys on alias, so a string with several entries cannot live there; it lives here, one
-- row per entry. Written only by scripts/load_lexicon.py from the researcher's
-- data/reference/lexicon/ingredient_splits.csv (rule 4: the file is the approval).

CREATE TABLE ingredient_alias_splits (
  alias             TEXT NOT NULL,
  canonical_id      TEXT NOT NULL REFERENCES canonical_ingredients,
  approved_by_human BOOLEAN NOT NULL DEFAULT true,
  PRIMARY KEY (alias, canonical_id)
);
