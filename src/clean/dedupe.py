"""Deduplication similarity primitives — CLAUDE.md §7.2, mechanical half only.

§7.2 names two similarity measures for flagging duplicate recipes: "exact
`content_hash` first, then Jaccard > 0.85 on canonical ingredient sets **and** fuzzy
title ratio > 0.8 -> flagged for review." Both functions below implement exactly the
measures named, as pure functions over whatever sets/strings the caller has.

**Deliberately not built here.**

- **A fixed threshold.** §7.2 states two different numbers for what reads as the same
  ingredient-set Jaccard check: the summary sentence earlier in the same section says
  "deduplicate on ingredient-set Jaccard > 0.9", the "detail worth keeping from the v2
  prompts" paragraph says "Jaccard > 0.85". Baking in either would silently resolve a
  discrepancy that is the document's, not a bug in this module — flagged here and in
  `docs/decisions.md` instead. Callers pass whatever threshold they intend; this
  module does not default one.
- **Any actual dedup decision.** A pair clearing both thresholds is *flagged for
  review*, not deduplicated — HD-12 ("review flagged duplicate pairs; set the
  source-precedence retention rule") decides which of a flagged pair survives, and on
  what rule. That is the researcher's call.
- **`cluster_id` assignment.** "Every retained recipe gets a `cluster_id`... that
  `cluster_id` is what CV folds group on" (§7.2) is the output of running these
  functions over the loaded corpus and applying HD-12's retention rule, in that
  order — not something a similarity function can assign on its own.
- **Ingredient-set Jaccard against real data.** `canonical_ingredients` is empty until
  HD-6, so there is no real canonical ingredient set to compute Jaccard over yet.
  `jaccard_similarity` works on any two sets of strings — raw ingredient names today,
  canonical ids once HD-6 closes — so nothing here needs to change when it does.
"""

from __future__ import annotations

from difflib import SequenceMatcher


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    """|intersection| / |union|, in [0.0, 1.0].

    Two empty sets return 1.0, not 0.0: there is nothing between them to disagree
    about, and 0.0 would read as "maximally different" for a pair that is arguably
    identical (both empty).
    """
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def title_similarity(a: str, b: str) -> float:
    """difflib's ratio: 2 * matching characters / total length, in [0.0, 1.0].

    A standard, library-provided measure, used rather than a bespoke string-distance
    metric — §7.2 already pins the threshold (0.8) numerically; inventing a new
    distance function on top of that number would just move the judgment call
    somewhere less visible.
    """
    return SequenceMatcher(None, a, b).ratio()
