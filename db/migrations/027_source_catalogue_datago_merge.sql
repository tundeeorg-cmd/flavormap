-- 027  source_catalogue: merge in data.go.th's export.
--
-- flavormap_datago_catalog.csv is a second catalogue export, structurally different
-- from gdcatalog's (no dataset_slug, a separate page-vs-resource URL split, its own
-- flavormap_layer/relevance_score bucketing) but describing the same kind of thing —
-- one row per dataset. Task 3 of the datago_catalog brief asks for one merged table
-- with provenance, not two parallel ones.
--
-- dataset_slug relaxed to nullable: data.go.th's export carries no slug at all, so
-- it can no longer be the universal natural key. `row_hash` (sha256 of the fields
-- that identify one catalogue row, computed by the loader) is the upsert key for
-- both catalogue_source values now — nullable with a unique index rather than a hard
-- NOT NULL constraint, so a future third catalogue with its own missing fields does
-- not force another migration just to relax a constraint again.
--
-- Duplicates across the two catalogues are FLAGGED, never silently merged or
-- dropped. `duplicate_of_catalogue_id` is populated by
-- `src/ingest/catalogue_merge.py`'s detection (Task 3a: exact `direct_resource_url`
-- match first — the brief's own "most reliable" — then `dataset_title_th` +
-- organisation match as a weaker signal). Which of a duplicate pair is authoritative
-- is a source-precedence call in the same class as HD-12 (recipe dedup retention)
-- and is not decided by this migration or by the loader.

ALTER TABLE source_catalogue ALTER COLUMN dataset_slug DROP NOT NULL;
ALTER TABLE source_catalogue DROP CONSTRAINT source_catalogue_dataset_slug_key;

ALTER TABLE source_catalogue
  ADD COLUMN row_hash         TEXT,
  ADD COLUMN catalogue_source TEXT NOT NULL DEFAULT 'gdcatalog'
               CHECK (catalogue_source IN ('gdcatalog', 'datago')),

  -- datago-specific fields. NULL on every gdcatalog-sourced row, same treatment
  -- `tier` already gets: carried through as provenance, never as a content filter
  -- or a priority order (Task 2b — relevance_score is confirmed inverted; see
  -- score_note and docs/decisions.md).
  ADD COLUMN page_url         TEXT,   -- what a human checks (datago's dataset_page_url)
  ADD COLUMN flavormap_layer  TEXT,   -- datago's own bucket (1_dish_culture, ...)
  ADD COLUMN relevance_score  REAL,
  ADD COLUMN score_note       TEXT,
  ADD COLUMN geo_coverage     TEXT,

  ADD COLUMN duplicate_of_catalogue_id BIGINT REFERENCES source_catalogue (catalogue_id);

COMMENT ON COLUMN source_catalogue.resource_url IS
  'The fetchable file URL — gdcatalog''s own resource_url, or datago''s '
  'direct_resource_url. What a fetcher uses; page_url is what a human checks.';

CREATE UNIQUE INDEX source_catalogue_row_hash_idx ON source_catalogue (row_hash)
  WHERE row_hash IS NOT NULL;
CREATE INDEX source_catalogue_catalogue_source_idx ON source_catalogue (catalogue_source);
CREATE INDEX source_catalogue_duplicate_of_idx ON source_catalogue (duplicate_of_catalogue_id);
