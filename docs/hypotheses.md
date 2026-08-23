# Pre-registration

What the researcher expects to find, for each of the five research questions, **written
and committed before any analysis runs**.

## Why this file exists

A negative result reported after the fact reads as an excuse. The same result reported
against a dated, committed prediction reads as a finding. This file is what converts the
negative-results section from a liability into the most credible part of the paper
(Bible §4, §12).

It is trivially cheap and unusual for a student project, which is exactly why it is worth
doing.

## Rules

1. **Predictions are the researcher's and only the researcher's.** Claude Code does not
   write in this file. An agent-written prediction is worthless — it is a guess by a system
   that has read the same data, and it cannot be evidence of what a person expected.
2. **Committed and dated before analysis.** A prediction added after seeing a result is not
   a prediction. The git timestamp is the whole mechanism.
3. **Wrong predictions stay.** Do not edit a prediction after the result is known. Report
   where the expectation was wrong — that is the point of the exercise.
4. **One prediction per RQ, plus a stated direction where there is one.** "I expect a
   change point somewhere" is not falsifiable; "I expect a discontinuity between 200 and
   400 km, sharpest on the Northeast/Central boundary" is.

## To be written before analysis begins

Bible §19 places this in the Aug–Sep 2026 window, before the first analysis runs.

**About the scaffold below.** The criteria, the named analysis and the empty fields were
written by Claude Code on 2026-08-23, on explicit instruction, to make each prediction a
short job rather than a blank page. **Every `Prediction:` line is empty and stays empty
until the researcher fills it.** Rule 1 is unchanged and unweakened: what the scaffold
supplies is the shape of a falsifiable claim, not the claim. If a criterion below looks
like it is steering toward an answer, delete it — it has overstepped.

Fill a prediction in, then tick its box and commit. **Commit each one as you write it**
rather than all five at the end; the git timestamp is the mechanism, and one commit for
five predictions dates them all to whenever the last was finished.

---

### RQ1 — Are cultural boundaries discrete or continuous?

- [ ] written

*Analysis that will test it:* distance-decay curve, cosine distance on TF-IDF against
great-circle km, with change-point detection; Louvain communities against the linguistic
boundary set. Mantel by permutation, 9,999 permutations (§5). **Figure 2.**

*A falsifiable prediction here states:* (a) discrete or smooth; (b) if discrete, a
kilometre range for the change point; (c) which single boundary is sharpest.

*Decide before writing:* at a 1.3% labelled fraction §4's own constraint fires and this
runs at region level, four to six units, not 77 provinces. Region-level claims cover 157
pages. Write the prediction for the corpus that will exist, and say which unit you mean.

**Prediction:**
**Date:**

---

### RQ2 — Is distinctiveness constituted by inclusion or by exclusion?

- [ ] written

*Analysis that will test it:* decomposition of each unit's distinctiveness into
presence-driven and absence-driven components, validated against interview Q9 responses
on stated absences. The measure itself is **HD-13** and does not exist yet. **Figure 3.**

*A falsifiable prediction here states:* at least one named unit expected **above** the
diagonal (defined by refusal) and one expected **below**. A prediction that some units
will differ from others is not falsifiable.

*Note:* this prediction can be written before HD-13 settles the measure. If the eventual
measure makes the prediction untestable as worded, say so in the results — do not rewrite
it (rule 3).

**Prediction:**
**Date:**

---

### RQ3 — How much is legible at all? — **closed, exploratory**

- [x] not registered, deliberately

The labelled-recipe fraction ran on 2026-08-23 before any prediction was written, and the
top of the per-province distribution was printed in the same run. That makes the
threshold-sensitivity result — how many provinces clear 10, 15 and 25 recipes — largely
foreseeable, not merely the headline fraction. A prediction written now would look like
pre-registration without being it.

**RQ3 is reported as exploratory.** State that in the methods alongside Figure 4's
exception. See `docs/labelled_fraction.md` and the two notes in `docs/decisions.md`.

The other four RQs are unaffected: nothing in their analyses has been run or seen.

---

### RQ4 — Which ingredients hold the cuisine together?

- [ ] written

*Analysis that will test it:* node-removal robustness on the PMI-weighted co-occurrence
network; delete each ingredient, measure fragmentation of regional subgraphs, rank by
structural indispensability. Depends on the lexicon (**HD-6**, **HD-10**). **Figure 5.**

*A falsifiable prediction here states:* (a) the top three ingredients by structural
indispensability, ranked; (b) which regional subgraph fragments first.

*Note:* (a) may well be easy and right, which makes it weak evidence on its own. (b) is
where the prediction earns its place. RQ4 is paper-optional per §4 — predict it anyway,
it costs one sentence.

**Prediction:**
**Date:**

---

### RQ5 — Does regional signal concentrate in vernacular practice?

- [ ] written

*Analysis that will test it:* classifier run separately per dish category, reported at
region level, against the majority-class baseline. The taxonomy is **HD-9** and is seeded
empty. **Figure 6.**

*A falsifiable prediction here states:* (a) the expected ordering of the dish categories
by accuracy; (b) a minimum margin over the majority-class baseline for the top category.
Without (b) the prediction cannot fail — any ordering is consistent with accuracy at
baseline.

*Decide before writing:* the categories do not exist until HD-9 does. Either settle HD-9
first, or write the prediction over the five candidate categories named in §4 (nam prik,
everyday/preserved, curries, restaurant-facing, desserts) and note that the taxonomy may
move under it.

**Prediction:**
**Date:**

---

*Created 2026-08-16, empty of predictions by design. Scaffold added 2026-08-23; the
prediction fields remain empty and are the researcher's alone.*
