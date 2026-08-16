-- 014  HD-2(b) (decided 2026-08-16, option B): border_country becomes TEXT[].
--
-- Two provinces border two countries each — Chiang Rai (Myanmar, Laos) and Ubon
-- Ratchathani (Laos, Cambodia). The pipe-delimited string that held them needed
-- splitting at every call site, and eventually one call site would forget.
--
-- HD-2(a) (decided: land borders only) is a data decision, not a schema one: Pattani
-- has maritime proximity to Malaysia and no land border, so it carries no border
-- country. That divergence between the administrative definition and the cultural
-- reality is recorded in docs/limitations.md (L17) rather than encoded here.

ALTER TABLE provinces
  ALTER COLUMN border_country TYPE TEXT[]
  USING CASE
          WHEN border_country IS NULL OR border_country = '' THEN NULL
          ELSE string_to_array(border_country, '|')
        END;

ALTER TABLE provinces
  ADD CONSTRAINT provinces_border_country_check
  CHECK (border_country IS NULL OR border_country <@ ARRAY['LA','KH','MM','MY']);

CREATE INDEX provinces_border_country_idx ON provinces USING GIN (border_country);

COMMENT ON COLUMN provinces.border_country IS
  'HD-2. LAND borders only, ISO 3166-1 alpha-2. NULL for interior provinces. '
  'Maritime proximity is deliberately excluded — see limitations L17 (Pattani).';
