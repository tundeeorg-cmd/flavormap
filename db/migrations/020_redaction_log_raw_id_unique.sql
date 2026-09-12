-- 020  redaction_log.raw_id UNIQUE — the same re-parse duplication gap as 019, one
-- table over.
--
-- Both loaders' INSERT INTO redaction_log has no ON CONFLICT guard either. Re-running
-- either loader against an already-parsed document produced a fresh redaction_log row
-- every time, all pointing at the same raw_id with identical counts — verified: three
-- runs against one synthetic document produced three rows. The table's own comment
-- already says "One row per parsed document"; this migration enforces that rather than
-- assuming it. NULL raw_id (should one ever occur) is unaffected — Postgres does not
-- treat NULLs as conflicting with each other under a UNIQUE constraint.

ALTER TABLE redaction_log ADD CONSTRAINT redaction_log_raw_id_key UNIQUE (raw_id);
