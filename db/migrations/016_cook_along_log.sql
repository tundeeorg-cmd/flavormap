-- 016  cook_along_log — RQ4's validation instrument (Bible §7.4, CLAUDE.md §4 RQ4).
--
-- RQ4 asks whether the *cleaned* dataset's ingredient list is still cookable. The
-- method is to cook 8 dishes from the normalised list (not the original source page)
-- and log what happened. This table is that log, seeded empty: no cook-along has run
-- yet, and no row here is a placeholder measurement.
--
-- Figure 4 (pipeline fidelity) reads the five fidelity_* columns as its matrix cells:
-- 8 dishes x {quantities, order, technique, specificity, completeness}, each cell
-- survived / degraded / lost, exactly as CLAUDE.md §6 specifies. NULL means not yet
-- cooked, never a guessed rating.

CREATE TABLE cook_along_log (
  log_id                  BIGSERIAL PRIMARY KEY,
  recipe_id               BIGINT NOT NULL REFERENCES recipes,
  cook_date               DATE,

  -- Cooked from the cleaned dataset's ingredient list, not the source page — the point
  -- is to test what the pipeline produced, per Bible §7.4.
  missing_ingredients     TEXT,   -- present on the source page, absent after cleaning
  substitutions_made      TEXT,   -- what was substituted, and why
  normalization_losses    TEXT,   -- what the pipeline visibly destroyed (order, technique, ...)
  result_recognizable     BOOLEAN,-- did the dish come out as the named dish
  classifier_gets_wrong   BOOLEAN NOT NULL DEFAULT false,  -- Bible §7.4: include >=2 of these

  fidelity_quantities     TEXT CHECK (fidelity_quantities   IN ('survived','degraded','lost')),
  fidelity_order          TEXT CHECK (fidelity_order        IN ('survived','degraded','lost')),
  fidelity_technique      TEXT CHECK (fidelity_technique    IN ('survived','degraded','lost')),
  fidelity_specificity    TEXT CHECK (fidelity_specificity  IN ('survived','degraded','lost')),
  fidelity_completeness   TEXT CHECK (fidelity_completeness IN ('survived','degraded','lost')),

  notes                   TEXT
);

CREATE INDEX cook_along_log_recipe_idx ON cook_along_log (recipe_id);
