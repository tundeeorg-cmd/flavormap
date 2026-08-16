-- 011  redaction_log — evidence that PDPA stripping actually ran.
--
-- One row per parsed document. A document that yields ZERO redactions is treated as a
-- parser failure, not as a clean document: institutional forms always carry contact
-- fields, so zero means the parser missed the block entirely.

CREATE TABLE redaction_log (
  redaction_id     BIGSERIAL PRIMARY KEY,
  raw_id           BIGINT REFERENCES raw_recipes,
  source_id        TEXT NOT NULL REFERENCES sources,
  document_ref     TEXT NOT NULL,           -- on-disk path or stable document identifier
  parsed_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

  n_names          INTEGER NOT NULL DEFAULT 0,
  n_addresses      INTEGER NOT NULL DEFAULT 0,
  n_phone_numbers  INTEGER NOT NULL DEFAULT 0,
  n_emails         INTEGER NOT NULL DEFAULT 0,
  n_coordinates    INTEGER NOT NULL DEFAULT 0,
  n_media_links    INTEGER NOT NULL DEFAULT 0,
  n_total          INTEGER GENERATED ALWAYS AS
                     (n_names + n_addresses + n_phone_numbers + n_emails
                      + n_coordinates + n_media_links) STORED,

  suspected_parser_failure BOOLEAN NOT NULL DEFAULT false,
  note             TEXT
);

CREATE INDEX redaction_log_failure_idx ON redaction_log (suspected_parser_failure);
