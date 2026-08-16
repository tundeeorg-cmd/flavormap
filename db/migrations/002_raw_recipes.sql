-- 002  raw_recipes — IMMUTABLE, append-only (rule 1).
--
-- v3: no raw_html column. Raw pages persist to data/raw/{source_id}/{hash}.{ext} on
-- disk only; duplicating them into Postgres inflates the database for no benefit
-- (Bible §7, §11). The table stores the path, not the payload.

CREATE TABLE raw_recipes (
  raw_id         BIGSERIAL PRIMARY KEY,
  source_id      TEXT NOT NULL REFERENCES sources,
  source_url     TEXT,
  fetched_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  http_status    INTEGER,

  -- Path to the raw page on disk. NOT NULL: a raw row without its source document
  -- cannot be re-parsed, which defeats the point of keeping raw data at all.
  raw_path       TEXT NOT NULL,

  -- Publication / post date from the source. Free to capture now and impossible to
  -- backfill after the freeze (Bible §7). Every scraper must attempt it; NULL means
  -- the source did not expose one, never that we did not look.
  published_at   DATE,

  parsed_json    JSONB,                     -- best-effort parse at fetch time
  content_hash   TEXT NOT NULL              -- sha256 of normalised text, for dedupe
);

CREATE UNIQUE INDEX raw_recipes_source_hash_idx ON raw_recipes (source_id, content_hash);
CREATE INDEX raw_recipes_published_at_idx ON raw_recipes (published_at);
