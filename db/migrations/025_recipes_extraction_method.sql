-- 025  recipes.extraction_method — parsed | manual (HD-35, researcher's request 2026-10-06).
--
-- Nakhon Nayok's three DCP forms (east_5_1..3) are image scans with no text layer. The
-- researcher chose hand transcription over OCR, and asked that manually transcribed
-- records be flagged so they can always be told apart from what the parser read.
--
-- Every row that exists when this runs was produced by a parser: dcp_food by
-- scripts/parse_dcp.py, kapook_cooking by scripts/parse_kapook.py. So all are backfilled
-- 'parsed', derived from how they were made, not guessed. The column is then NOT NULL
-- with **no default**: a loader that forgets to set it fails, rather than silently
-- labelling a hand transcription 'parsed'.

ALTER TABLE recipes ADD COLUMN extraction_method TEXT
  CHECK (extraction_method IN ('parsed', 'manual'));

UPDATE recipes r SET extraction_method = 'parsed'
  FROM raw_recipes rr
 WHERE rr.raw_id = r.raw_id AND rr.source_id IN ('dcp_food', 'kapook_cooking');

ALTER TABLE recipes ALTER COLUMN extraction_method SET NOT NULL;
