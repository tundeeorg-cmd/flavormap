-- 006  provinces — reference data, committed to git as data/reference/provinces.csv.
--
-- Ordering note: this migration comes BEFORE province_attribution (007), which has a
-- foreign key into it. The v2 plan numbered them the other way round, which cannot
-- apply from an empty database.

CREATE TABLE provinces (
  province_code  TEXT PRIMARY KEY,          -- ISO 3166-2:TH, e.g. 'TH-32'
  name_th        TEXT NOT NULL,
  name_en        TEXT NOT NULL,
  region4        TEXT NOT NULL CHECK (region4 IN ('North','Northeast','Central','South')),

  -- HD-1. Deliberately nullable: the five-way split has genuinely ambiguous provinces
  -- and this column stays empty until the researcher decides. NOT NULL here would
  -- force a guess, and rule 2's spirit is that a guessed label is worse than no label.
  dialect_group  TEXT,

  -- HD-2. Which countries this province borders by land, NULL for interior provinces.
  border_country TEXT,                      -- LA | KH | MM | MY | NULL

  centroid_lat   DOUBLE PRECISION NOT NULL,
  centroid_lon   DOUBLE PRECISION NOT NULL,
  geom           GEOMETRY(MultiPolygon, 4326)  -- loaded by scripts/load_geometry.py
);

CREATE INDEX provinces_geom_idx ON provinces USING GIST (geom);
CREATE INDEX provinces_region4_idx ON provinces (region4);
