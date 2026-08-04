CREATE TABLE sources (
  source_id      TEXT PRIMARY KEY,          -- 'doae', 'tat', 'wongnai', 'interview', 'cookbook'
  source_type    TEXT NOT NULL,             -- web_scraped | interview | cookbook | institutional
  base_url       TEXT,
  robots_ok      BOOLEAN NOT NULL,
  audited_on     DATE NOT NULL,
  est_recipes    INTEGER,
  province_quality TEXT                     -- explicit | region_only | none
);
