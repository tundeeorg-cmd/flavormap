-- 030  Lexicon provenance (researcher, 2026-11-06).
--
-- drafted_by: who drafted the entry, 'bo' (the researcher) or 'claude' (the agent, at
-- the researcher's request). reviewed_by_bo: the date the researcher confirmed a drafted
-- entry, NULL until then. Written only by scripts/load_lexicon.py from
-- data/reference/lexicon/canonical_ingredients.csv. The temporary default only fills
-- rows that exist before the next load; it is dropped so no future row can omit it.

ALTER TABLE canonical_ingredients ADD COLUMN drafted_by TEXT NOT NULL DEFAULT 'bo'
  CHECK (drafted_by IN ('bo', 'claude'));
ALTER TABLE canonical_ingredients ALTER COLUMN drafted_by DROP DEFAULT;
ALTER TABLE canonical_ingredients ADD COLUMN reviewed_by_bo DATE;

COMMENT ON COLUMN canonical_ingredients.drafted_by IS
  'Provenance: bo = researcher, claude = agent-drafted at the researcher''s request.';
COMMENT ON COLUMN canonical_ingredients.reviewed_by_bo IS
  'Date the researcher confirmed an agent-drafted entry; NULL = not yet reviewed.';
