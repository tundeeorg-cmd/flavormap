-- 022  cook_along_log.log_key — a stable natural key so the loader can upsert.
--
-- scripts/load_cook_along.py reads one hand-written TOML file per cook-along from
-- data/cook_along/. Without a key tied to that file, re-running the loader would insert
-- a fresh row every time — the same re-parse duplication gap migrations 019 and 020
-- closed for recipes and redaction_log. log_key is the file's stem (e.g.
-- "2026-10-04_khao_soi"), so editing a file and reloading updates its row in place.
--
-- NOT NULL is safe to add directly: 016 seeded the table empty and nothing has
-- written to it before this migration.

ALTER TABLE cook_along_log ADD COLUMN log_key TEXT NOT NULL;
ALTER TABLE cook_along_log ADD CONSTRAINT cook_along_log_log_key_key UNIQUE (log_key);
