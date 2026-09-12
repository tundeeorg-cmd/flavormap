-- 025  source_catalogue — a source *inventory*, not recipe data.
--
-- Tracks every dataset seen in culture.gdcatalog.go.th's catalogue export
-- (flavormap_gdcatalog_sources_full.csv / ..._tierA_core.csv): what it is, how it was
-- classified, and whether/why it was harvested. This table is never joined into
-- ingredient-based analysis — it is the honest record of what Thai open data
-- actually contains about regional food, which is itself a methods-section artifact
-- (the brief's own framing, Task 1).
--
-- All ten source columns are kept as TEXT, deliberately, including the ones that
-- look numeric or date-shaped (n_resources, last_modified). This project has been
-- burned once already by assuming a source field's format without seeing real data
-- (HD-23's region-scheme surprises); this file has never been available in any
-- session that has touched it, so nothing about its actual formatting is confirmed.
-- A loader is free to additionally derive a typed column later once real rows exist
-- to check the assumption against.

CREATE TABLE source_catalogue (
  catalogue_id     BIGSERIAL PRIMARY KEY,
  dataset_slug     TEXT NOT NULL UNIQUE,     -- the catalogue's own stable identifier

  tier             TEXT,                     -- 'A' | 'B', carried through as provenance
                                              -- ONLY — never the content filter. See
                                              -- src/ingest/source_catalogue.py's module
                                              -- docstring for why (Task 0b).
  dataset_title_th TEXT NOT NULL,
  province_th      TEXT,
  publisher_th     TEXT,
  description_th   TEXT,
  formats          TEXT,
  n_resources      TEXT,
  last_modified    TEXT,
  resource_url     TEXT,

  -- Task 1b's closed vocabulary. A mechanical keyword classification
  -- (src/ingest/source_catalogue.py), not a content judgement — 'irrelevant' means
  -- "no keyword matched", not "a human read this and decided it was irrelevant".
  content_class    TEXT NOT NULL
                     CHECK (content_class IN (
                       'local_dish_inventory', 'gi_registration', 'restaurant_registry',
                       'agricultural_production', 'cultural_heritage', 'tourism',
                       'irrelevant'
                     )),

  assessed_at      TIMESTAMPTZ,               -- when a human reviewed this row; NULL
                                              -- until they do, even if content_class
                                              -- and harvest_status are already set
  harvest_status   TEXT NOT NULL DEFAULT 'not_assessed'
                     CHECK (harvest_status IN
                       ('not_assessed', 'rejected', 'queued', 'harvested', 'failed')),
  rejection_reason TEXT,

  CHECK ((harvest_status = 'rejected') = (rejection_reason IS NOT NULL))
);

CREATE INDEX source_catalogue_class_idx ON source_catalogue (content_class);
CREATE INDEX source_catalogue_status_idx ON source_catalogue (harvest_status);
CREATE INDEX source_catalogue_province_idx ON source_catalogue (province_th);
