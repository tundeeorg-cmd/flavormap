-- 010  coverage — RQ3 is built on this table, and it ships as a first-class release
--      file (coverage.csv, Bible §16).
--
-- Recomputed by the pipeline rather than hand-maintained; one row per province per
-- computation run, so threshold sweeps and pre/post-freeze comparisons stay auditable.

CREATE TABLE coverage (
  coverage_id       BIGSERIAL PRIMARY KEY,
  computed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  province_code     TEXT NOT NULL REFERENCES provinces,

  recipe_count      INTEGER NOT NULL,
  labelled_count    INTEGER NOT NULL,       -- rows with a non-NULL province_code
  labelled_fraction REAL,

  -- Source-domain concentration: what share of this province's recipes come from its
  -- single largest source domain. A province visible only through one site is not
  -- meaningfully covered, and RQ3's argument depends on being able to say so.
  top_source_id     TEXT REFERENCES sources,
  top_source_share  REAL,
  distinct_sources  INTEGER,

  -- Carried so institutional and web-scraped coverage are never silently pooled
  -- (limitations L14–L16).
  source_type       TEXT
);

CREATE INDEX coverage_province_idx ON coverage (province_code, computed_at DESC);
