# Decision log

Every `[HD]` gate in FlavorMap — the judgment calls that are the project's intellectual
content. Twenty gates, roughly 225 hours (Bible §13).

**This file is not bookkeeping.** It is interview preparation, methods-section source
material, and the single best answer to "how much help did you have?" A student who can
open a dated file and show two hundred documented judgment calls is not answering that
question defensively.

## How to use it

Claude Code may append a **stub** — the gate number, the date, the options presented, and
the consequences of each. **The Decision and Reasoning fields are the researcher's and are
never written by the agent.** A gate with an empty Decision field is an open gate, and no
work proceeds past it.

Format per gate:

```
## HD-n — <short title>
**Date presented:** YYYY-MM-DD
**Options presented:**
  A. …  (consequence: …)
  B. …  (consequence: …)
**Recommendation given:** …
**Decision:**            ← researcher
**Reasoning:**           ← researcher
**Date decided:**        ← researcher
```

Gates are listed in `CLAUDE.md` §9. Numbering there is a proposal reconciled from the v2
plan; confirm it before citing a gate number anywhere external.

---

*First entry: 2026-08-16. No gates decided yet.*

## HD-1 — Dialect-group assignment for the 77 provinces
**Date presented:** 2026-08-16
**Status:** OPEN — and as of 2026-08-22 `provinces.dialect_group` is **populated with
the unreviewed option-B proposal**, not NULL. See the loading note below.

**What depends on it:** RQ1's competing boundary set. Bible §5 RQ1 scope note picks
*linguistic* as the one comparison to run, so this column is the entire alternative
hypothesis. It also feeds `D_lang` in any partial-Mantel table and the upper-vs-lower
Isaan question that Surin was chosen to sit on.

**Options presented:**
  A. Five-way split (Central / Kam Mueang / Isaan-Lao / Dambro-Southern / Malay), assign
     ambiguous provinces to their majority group.
     Consequence: clean categorical variable, one province one label. Boundary provinces
     are misdescribed, and they are exactly where RQ1 looks for a change point.
  B. Five-way split with an explicit `transitional` sixth value for the ambiguous set.
     Consequence: honest, and `transitional` provinces can be reported separately or
     excluded in a sensitivity run. Costs a category that no ethnolinguistic map uses.
  C. Per-province membership weights over the five groups instead of a single label.
     Consequence: most faithful to the linguistic reality and supports a continuous
     `D_lang`. Substantially more work, and no published source gives the weights — they
     would be judgment calls needing individual defence.

**Recommendation given:** B.
**Consequence of choosing otherwise:** A makes the RQ1 result harder to defend precisely
at the boundaries the question is about. C is defensible but adds ~10 hours of sourcing
and turns one gate into fifteen.

**Ambiguous provinces found:** Tak, Phetchaburi, Ratchaburi, Chumphon, Prachuap Khiri
Khan, Uthai Thani, Nakhon Sawan, Phetchabun, Loei, Nakhon Ratchasima, Kanchanaburi,
Satun. Rationale for each is in the session report accompanying this entry.

**Selected: option B** (communicated in session, 2026-08-16).

*Implementation note (machine-written, not a substitute for the fields below).*
Migration `013_dialect_group_taxonomy.sql` adds a CHECK constraint permitting
`Central | Kam_Mueang | Isaan_Lao | Dambro | Malay | Transitional`. NULL remains
permitted — an unassigned province is honest, a wrongly-assigned one is not.
`data/reference/provinces.csv` is populated: Central 26, Isaan_Lao 18, Transitional 12,
Kam_Mueang 9, Dambro 9, Malay 3. **The per-province assignment is a proposal and has not
been reviewed** — see the session report for the three calls most worth checking
(Surin/Si Sa Ket/Buri Ram, Sukhothai/Phitsanulok, Nakhon Ratchasima).

*Loading note, 2026-08-22 (machine-written).* `scripts/load_geometry.py` has now been run
and all 77 rows are in `provinces`, with the same distribution as the CSV. This was a
deliberate choice to keep the database usable while the gate is open, taken in session on
2026-08-22 when the alternative — loading everything except this column — would have meant
a second load later. **The column therefore holds an unreviewed proposal and must not be
read as decided.** Nothing downstream may cite `dialect_group` until the fields below are
filled. To revert to the state this entry originally described:

```sql
UPDATE provinces SET dialect_group = NULL;
```

The earlier claim in this entry that the column "is NULL for all 77 rows and stays that way"
was accurate when written and is superseded by this note.

**Decision:**
**Reasoning:**
**Date decided:**

---

## HD-2 — Land-border definition
**Date presented:** 2026-08-16
**Status:** OPEN — `provinces.border_country` is populated with land borders only, and the
multi-border encoding is provisional.

**What depends on it:** `D_border` in any boundary comparison, and the "border province"
framing in RQ1/RQ3 discussion.

**Two questions, one gate.**

**(a) Does coastal proximity to Malaysia count as a border?**
  A. Land borders only. Satun, Songkhla, Yala, Narathiwat are MY; nothing else.
     Consequence: defensible, matches every official boundary dataset. Excludes Pattani,
     which is culturally continuous with the Malay-speaking south and has obvious
     maritime contact but no land border.
  B. Land borders plus maritime adjacency. Adds Pattani (and arguably Trang, Krabi,
     Phuket for Andaman-side contact).
     Consequence: better matches culinary reality in the deep south. "Maritime adjacency"
     has no standard definition, so the threshold becomes another judgment call to defend.

**Recommendation given:** A, with Pattani noted in the limitations register as a known
case where the administrative definition and the cultural reality diverge.

**(b) How are multi-border provinces encoded?** Chiang Rai borders both Myanmar and Laos;
Ubon Ratchathani borders both Laos and Cambodia. `border_country` is a single TEXT column.
  A. Pipe-delimited string (`MM|LA`) — what the CSV currently holds. Cheap; needs parsing
     everywhere and cannot be indexed or joined cleanly.
  B. `TEXT[]` array via a forward migration. Queryable, indexable, honest about
     cardinality. Costs one migration.
  C. A `province_borders` junction table. Most normalised; heaviest for two rows of data.

**Recommendation given:** B.
**Consequence of choosing otherwise:** A works but every consumer re-implements the split
and one of them will forget. C is correct and disproportionate at n=2.

**Selected: (a) option A, (b) option B** (communicated in session, 2026-08-16).

*Implementation note (machine-written, not a substitute for the fields below).*
(a) Land borders only. Pattani carries no `border_country`; the divergence from cultural
reality is recorded as limitation L17 rather than encoded.
(b) Migration `014_border_country_array.sql` converts `border_country` to `TEXT[]` with a
CHECK against `{LA,KH,MM,MY}` and a GIN index. Chiang Rai and Ubon Ratchathani are the two
multi-border rows. The CSV keeps the pipe-delimited form because CSV has no array type;
`scripts/load_geometry.py` splits on load.

**Decision:**
**Reasoning:**
**Date decided:**

---

## HD-3 (dcp_food) — Does `food.culture.go.th`'s `ai-train=no` signal apply to this project?
**Date presented:** 2026-08-16
**Status:** OPEN — nothing has been fetched from this domain beyond `robots.txt`.

**The finding.** The site's robots.txt permits `FlavorMapResearchBot` to fetch every
candidate path (`User-agent: * → Allow: /`, confirmed with `urllib.robotparser`). The same
file separately:

- sets `Content-Signal: search=yes,ai-train=no,use=reference`
- states these are **express reservations of rights under Article 4 of EU Directive 2019/790**
- issues `Disallow: /` to nine named AI crawlers, including **ClaudeBot**

So the letter permits the fetch and the signal reserves rights against AI use. This
project sits in the gap: it is academic research, and it feeds fetched text to the Claude
API for field extraction, and it publishes a derived dataset to HuggingFace.

**Three separable questions:**

1. *Is fetching allowed?* Yes, unambiguously, for our UA.
2. *Is extraction with an LLM "ai-train"?* Almost certainly not — no model is trained or
   fine-tuned. It is closer to `ai-input`, which the operator left **unspecified**, meaning
   neither granted nor restricted. But the nine-crawler blocklist shows the operator's
   general intent regarding AI, and ClaudeBot is on it.
3. *Does releasing a derived dataset conflict with `ai-train=no`?* The release contains
   normalised ingredient lists, province labels and dates — **not recipe prose** (Bible §7
   and §16 already forbid publishing the text). Someone could still train on the derived
   fields. The mitigation is real but not total.

**Options presented:**
  A. **Proceed as planned.** Fetch, parse, publish derived fields only.
     Consequence: defensible on the letter, and the derived-only release is a genuine
     mitigation. Risk: a reviewer, or the Department itself, reads the ClaudeBot block and
     `ai-train=no` as covering exactly this and the project looks like it lawyered a
     signal rather than honoured it. This is a Thai government cultural-heritage body and
     the researcher is a Thai student — the relationship matters beyond this dataset.
  B. **Write to the Department first**, describe the project, and ask for written
     permission. Proceed on a yes; drop or restrict on a no or on silence after a stated
     deadline.
     Consequence: slowest, and the strongest possible position. A permission email in
     `ETHICS.md` converts the project's biggest ethical exposure into a credibility asset,
     and Bible §13's "how much help did you have" logic applies here too. Costs 1–3 weeks
     of calendar in a window that has slack (Bible §19 puts deliberate slack in Oct–Dec).
  C. **Use it as a reference layer only**, never redistributed: fetch, parse, use for the
     RQ3 coverage comparison, and exclude every DCP-derived row from the HuggingFace
     release.
     Consequence: honours `use=reference` almost literally. Keeps the analytical value —
     RQ3's institutional-vs-commercial comparison is the point of this corpus — while
     removing the redistribution question entirely. Costs a source-exclusion flag through
     the export path, which the schema already supports via `source_type`.
  D. **Drop the source.** Consequence: loses the complete-by-design 77-province baseline
     that makes RQ3 a comparison rather than a bare blank map. Materially weakens the
     strongest research question.

**Recommendation given:** **B, with C as the fallback** if there is no reply. They are
compatible: send the email now, start under C's constraints, and relax to A only on an
explicit yes. That way the calendar does not stall on a reply that may never come, and
nothing is published that would have to be retracted.

**Note on scale.** Whatever is decided, the fetch is ~231 PDFs at 1 req/sec — about four
minutes of traffic. Volume is not the concern here; permission is.

**Decision:**
**Reasoning:**
**Date decided:**

---

## HD-21 — Does ตำบล (subdistrict) enter the database?
**Date presented:** 2026-08-22
**Status:** OPEN — no sub-provincial column exists on the recipe side at all, so nothing
has been implemented in either direction. `ETHICS.md` currently states both answers.

**Numbering note.** Proposed as HD-21, *not* HD-4. This gate was called "HD-4" in session
on 2026-08-22 before the numbering was checked; `CLAUDE.md` §9 already assigns HD-4 to
"read 20 parsed recipes by hand and write the defect list." §9's own header flags its
numbering as a proposal, and the Bible describes twenty gates, so this is a twenty-first
surfaced by the DCP form. Renumber freely — but in `CLAUDE.md` §9 and this file together.

**Why this is open.** `ETHICS.md` contradicts itself inside one section:

> l.102–103 — forms "carry informant names, house numbers, roads, **subdistricts**,
> postcodes, and mobile numbers. These are **discarded during parsing**, before any write"
>
> l.108 — "Retained from such forms: administrative geography (**ตำบล** / อำเภอ / จังหวัด).
> Administrative geography is not contact detail."

ตำบล *is* subdistrict. The document says it is both discarded and retained. Separately, the
session brief of 2026-08-22 asks for district **and** subdistrict on the schema, while
`db/migrations/008_fieldwork.sql` comments "District only — never subdistrict-plus-address."
Three statements, three positions.

**What actually exists.** `informants.district` is the only sub-provincial column in the
schema. `recipes`, `raw_recipes` and `province_attribution` carry no district and no
subdistrict. Any option below needs a forward migration.

**Two streams, and the rule need not be the same for both.** `informants` holds people the
researcher interviews under written consent — PDPA data subjects in the ordinary sense. The
DCP corpus is a set of documents *already published by a government department*, where the
dish and its ตำบล are public and the personal data is the submitter's name, house number,
road, postcode and mobile. Treating the two identically is part of what produced the
contradiction. A decision that splits them is legitimate and should say so explicitly.

**Options presented:**
  A. **Province only.** Discard ตำบล and อำเภอ at parse time, both streams.
     Consequence: strongest PDPA position, no re-identification surface. Loses the
     sub-provincial stamping that is one of the few things making the DCP corpus richer
     than a bare province label. RQ1's distance-decay runs on province centroids anyway, so
     the analytical cost lands on future work and on provenance, not on the current paper.
  B. **Province + อำเภอ (district); discard ตำบล.** One rule across both streams.
     Consequence: matches the rule already written into `008_fieldwork.sql`, and makes
     `ETHICS.md` internally consistent with a two-word edit. ~900 อำเภอ nationally, mean
     population ~70k — not identifying alone. Loses the finest geography the forms carry.
  C. **Province + อำเภอ + ตำบล; discard only the contact block** (name, house number, road,
     postcode, mobile).
     Consequence: fullest provenance, and it is what `ETHICS.md` l.108 already claims the
     project does. Defensible on the grounds that the Department has itself published this.
     But ~7,255 ตำบล nationally, mean population ~9k, and this corpus is *deliberately
     curated for dishes at risk of disappearing* (L15) — a rare dish plus a 9,000-person
     subdistrict is a small haystack, and PDPA covers indirect identification.
  D. **Retain ตำบล in a column flagged non-exportable.** Kept for internal provenance and
     QA, excluded from every release, with HD-20's final read-through as backstop.
     Consequence: keeps the information without publishing it. But it is still "in a table,"
     which is exactly what the rule at the top of that `ETHICS.md` section says never
     happens — so choosing D means rewriting the rule, not just the retained-fields list.

**Recommendation given:** **B**, with the split stated explicitly: อำเภอ on both streams,
ตำบล on neither.

**Consequence of choosing otherwise:** C is the option with the strongest positive argument
— the data is already public — and if sub-provincial resolution turns out to matter for
RQ3's coverage cartography, C is what makes that possible. The reason to still prefer B is
that **the conservative choice is unusually cheap here**: the 231 raw PDFs are retained on
disk, so ตำบล can be recovered by re-parsing at any point. This is not the usual
irreversible discard. Taking the narrow option now costs one re-parse later if the
judgement changes, whereas taking C now and publishing means the disclosure cannot be
withdrawn. A is defensible but discards อำเภอ for no privacy gain that B does not already
secure. D is the honest form of C and should be chosen over C if the answer is "keep it but
never publish it."

**What this gate blocks.** The parser cannot be written until it is decided — the field list
is the parser's output contract, and `redaction_log`'s per-class counts depend on knowing
which classes are stripped. It also fixes the wording of `ETHICS.md` l.102–108, which stays
self-contradictory until then.

**Decision:**
**Reasoning:**
**Date decided:**

---

## Note — Figure 4 generated before pre-registration
**Date:** 2026-08-22
**This is not a gate.** It is a record of a rule being knowingly set aside, written so
the history does not have to be reconstructed later.

`docs/hypotheses.md` carries no predictions — all five RQ entries are still empty
checkboxes. The standing rule is pre-registration before analysis. Figure 4 is Bible §21
item 2, which is analysis. It was generated anyway, on the researcher's explicit
instruction in session on 2026-08-22, after the position was put and restated.

**What this costs.** The Figure 4 result cannot be cited as testing a prior prediction,
because none was registered. Any later claim that the regional pattern was expected is
unsupported by the repository, and the git history shows the figure preceding the
hypotheses file. Predictions written after this date describe a result already seen.

**What it does not cost.** Nothing else. The remaining four RQs are unaffected, and
registering predictions for them before their analyses still works normally. The
labelled-recipe fraction (§21 item 1) has not been run, and RQ3's prediction can still
be registered before it.

**Mitigating facts, stated rather than relied on.** This corpus cannot support the
figure's question anyway — the programme shortlists exactly three menus per province, so
per-province prevalence is confined to {0, ⅓, ½, ⅔, 1}, and L15 records that the corpus
is curated for rarity rather than sampled from practice. The figure is a demonstration
that the institutional corpus is the wrong instrument for RQ1-style prevalence work, not
a measurement of Thai cooking. The real Figure 4 needs the web corpus, which does not
exist yet.

**Recommended repair.** Write `docs/hypotheses.md` before the labelled-recipe fraction is
measured, and state in the paper's methods that Figure 4's exploratory version preceded
pre-registration while the confirmatory analyses did not. A stated exception is
defensible; a silent one is not.

---

## Note — the labelled-recipe fraction was measured before pre-registration

**Date:** 2026-08-23

The standing rule is pre-registration before analysis. `docs/hypotheses.md` still carries
no predictions — all five RQ entries are empty checkboxes — and the labelled-recipe
fraction is Bible §21 item 1, which is analysis, and the one the note of 2026-08-22
explicitly said RQ3 could still be registered ahead of. It was measured anyway, on
instruction in session.

**What it costs.** The 1.3% figure cannot be cited as testing a prior prediction about
RQ3, and an RQ3 prediction written after today describes a result already seen. This is
the second such exception; the first was Figure 4, one day earlier. Two is a pattern
rather than an accident, and the pattern is that analysis is running ahead of the file
meant to precede it.

**What it does not cost.** RQ1, RQ2, RQ4 and RQ5 are unaffected and can still be
registered normally. The measurement itself is not weakened — it is a descriptive count
with a hand audit attached, not a hypothesis test, and 1.3% against a 35% threshold is
not a result a prediction would have changed.

**Recommended repair.** Write the four remaining predictions in `docs/hypotheses.md`
before any further analysis runs, and state in the paper's methods that the two §21
blocking items preceded pre-registration while the confirmatory analyses did not.

## Evidence for HD-3 — the consumer-source go/no-go

**Date presented:** 2026-08-23

`docs/labelled_fraction.md` is the measurement HD-3 has been waiting on for
`kapook_cooking`: 2,521 pages with a readable ingredient list, of which **33 (1.3%)** carry
a province label that is a claim about the dish, against a §11 threshold of 35%.
Region-level claims reach 6.2%.

**Options presented:**
  A. **Keep the source, reframed.** Treat kapook as a coverage corpus rather than an
     attribution corpus: it answers RQ3 well and RQ1 not at all.
     (consequence: honest, and RQ3 becomes the project's spine. The province-level
     ambition in RQ1 has to be withdrawn or rebuilt on fieldwork and the DCP corpus.)
  B. **Build a second consumer source first** (`doae`, `tat`, `pantip_food`) and re-measure
     before deciding.
     (consequence: costs weeks. A second source would have to reach roughly 70% labelled
     to pull a combined corpus to 35%, which nothing in the audit suggests is likely.)
  C. **Drop the source.** (consequence: loses the only consumer corpus in hand and the only
     evidence for RQ3's central claim. Not recommended — a 1.3% labelled fraction is a
     finding, and rule 9 says negative results ship.)

**Recommendation given:** A, with the 78-row hand audit in
`docs/kapook_province_hits_audit.csv` confirmed by the researcher first. The `dish` /
`ingredient` boundary is a judgment call and the headline number rests on it.

**Audit confirmed 2026-08-23.** The researcher reviewed the 78 rows and agreed with all 33
`dish` calls. 1.3% is a confirmed figure. The go/no-go on the source itself — option A, B
or C above — is still open.

**Decision:** **A — keep the source, reframed.** kapook is a coverage corpus, not an
attribution corpus. Recorded from the researcher's instruction in session, 2026-08-23; the
choice is theirs, the transcription is the agent's.
**Reasoning:**            ← researcher. Still empty, and it is the field the methods
section will quote. The decision is recorded; the argument for it is not.
**Date decided:** 2026-08-23

**What A commits the project to.** RQ3 becomes the spine and leads the abstract, which §4
already said. RQ1's province-level form is withdrawn — §4's own constraint fires below 35%
— and whether it is rebuilt at region level on this corpus, rebuilt on fieldwork and the
DCP corpus, or dropped is **a separate decision and is not taken here**. The kapook fetch,
parse and storage rules continue unchanged under the 2026-08-22 audit.

**Not affected: HD-3 (dcp_food) above, which stays open.** That gate is about
`food.culture.go.th`'s `ai-train=no` signal and the ClaudeBot blocklist, and nothing has
been fetched from that domain beyond robots.txt. Two sources, two go/no-go decisions.

---

## Figure 2 replacement specification

**Date presented:** 2026-08-23
**Status:** OPEN. §6's Figure 2 row is marked not-buildable and stands until this is settled.

§6 specifies Figure 2 as a distance-decay scatter over ~2,900 province pairs. RQ1 now runs
on four regions, which give six pairs. The draft replacement is
`docs/figure2_spec_draft.md`: separation against geographic distance with permutation-null
intervals, plus a companion panel showing the six nulls, and no fitted line.

**Options presented:**
  A. **Adopt the draft as specified**, both panels, and load GADM so panel A's geographic
     axis exists.
     (consequence: keeps RQ1's geographic question in the frame and can show whether
     separation tracks distance — the answer to which is currently unknown. Costs the GADM
     load, which Figure 1 needs anyway.)
  B. **Adopt the fallback only** — forest plot, no geographic axis.
     (consequence: buildable today, no new dependency. Loses the ability to say anything
     about distance, which is what RQ1 was originally about.)
  C. **RQ1 ships without a figure**, leaning on the table in `docs/rq1_region_level.md`.
     (consequence: honest, and six points may not deserve a figure. Costs RQ1 its place in
     the figure list, and a reader skimming figures would not know the question was asked.)

**Recommendation given:** A. Figure 1 needs the GADM load regardless, so the marginal cost
is small, and whether compositional difference tracks distance is the closest thing to an
answer RQ1 still has. B is the right fallback if the geometry load proves troublesome.

**Decision:** **A — adopt the draft, both panels, with the geographic axis.** Recorded from
the researcher's instruction in session, 2026-08-23.
**Reasoning:**            ← researcher
**Date decided:** 2026-08-23

**Built and adopted the same day.** `scripts/make_figure2.py` + `src/viz/figure2.py`, wired
into `make figures`. The spec is now `docs/figure2_spec.md` and §6's row points at it.

*The GADM dependency was never unmet.* The draft recorded the geometry as absent; it was
read off `provinces.csv`, which ships with its centroid columns empty **by design** because
`load_geometry.py` derives them into the database rather than having 77 coordinate pairs
typed by hand. All 77 provinces already had `geom` and a centroid. Nothing had to be
downloaded. The draft's option B was therefore weighed against a cost that did not exist —
the decision is unaffected, since A was chosen and A is what was buildable, but a cost
estimate that wrong is worth recording rather than quietly correcting.

**The geographic axis earned itself.** The two closest region pairs are the two most
separated, and the farthest pair is not separated at all. Compositional difference does not
track distance at this resolution — a statement the forest-plot fallback could not have
made.

**Consequential edit made under this decision:** §4's RQ1 output — "a number in kilometres:
the width of the boundary zone" — is struck through and replaced. §4 and §6 now agree.

**Numbering decided 2026-08-23: it stays Figure 2.** It answers RQ1 and occupies RQ1's slot,
and the continuity is real — the same question, asked of a corpus that cannot support the
original form of it. The discontinuity is carried in the methods section rather than in the
figure number: Figure 2 was respecified after the labelled fraction came in at 1.3%, and the
distance-decay curve its first specification called for was never run. **This gate is now
fully closed.**

**Two things this decision drags with it, whichever way it goes.** §4's RQ1 output — "a
number in kilometres: the width of the boundary zone" — does not survive and needs
amending, or §4 and §6 will disagree. And a figure this far from its specification may
deserve a fresh number rather than inheriting Figure 2's, so that the paper's figure list
does not imply continuity with a distance-decay analysis that was never run.

**Decision:**
**Reasoning:**
**Date decided:**

---

## Evidence for RQ5 — the checkbox extraction go/no-go
**Date presented:** 2026-08-30
**Status:** OPEN. Bible §23 item 3 and §22's HIGH risk row both resolve here.

Full measurement and method: [`docs/checkbox_extraction.md`](checkbox_extraction.md).
Regenerate with `uv run python -m scripts.measure_dcp_fields`.

**The finding, in two parts.** The extraction works: endangerment is recovered on 157 of
231 documents (68.0%) against a corpus ceiling of 160 (69.3%), so the parser is within 1.3
points of everything that is there to get. The 32% gap is 71 documents where no value
exists to recover — §3 present but unticked (34), §3 absent from the form variant (25),
image-only scans (12) — plus three that were read individually, one a false positive of
the bucket test and two genuinely corrupted.

**And RQ5 still has no data.** §6 compares official endangerment against cooks in Nan and
Surin *on the same dishes*, and the state selected three dishes per province. RQ5's sample
is therefore six documents. Four carry an endangerment level. **All four carry the same
level — `transmitted`.** Figure 5 is specified as a confusion matrix whose off-diagonal
cells are the interesting ones; with one distinct official value there is no matrix, and
no answer the cooks give can produce one.

This is a question-design result, not an extraction failure, and it is not something a
better parser can fix.

**Options presented:**
  A. **Keep RQ5, reframed as an existence claim.** Report the four Nan/Surin dishes the
     state calls `transmitted` and ask whether cooks agree, without an agreement statistic.
     Consequence: honest and cheap, and §6 already uses this framing for RQ3 ("six of six
     cooks in Surin named…"). But it is a much smaller claim than "do cooks agree with the
     state", and Figure 5 does not survive in its specified form.
  B. **Widen the fieldwork provinces** so the official axis has variance. The corpus-wide
     distribution does vary — `near_lost` 105, `transmitted` 42, `lost` 10 — so provinces
     with a `near_lost` or `lost` dish exist and could be selected deliberately.
     Consequence: the strongest version of RQ5, and the only one that yields a real matrix.
     Costs a third trip, or replaces one of the two already planned. §22 already lists
     unbooked trips as the top risk; this raises that risk rather than lowering it.
  C. **Drop RQ5 and promote a replacement.** Consequence: §6 goes to four questions. §7
     already marks RQ5 "Conditional" and §22 says to "have a replacement question ready",
     so this is the pre-registered contingency firing exactly as designed — which is a
     methods-section asset, not a retreat.
  D. **Keep RQ5 against the full corpus**, comparing official endangerment to something
     other than fieldwork. Consequence: 157 documents is a real sample, but there are no
     cooks in it. Whatever it compares against, it is no longer the question §6 asks.

**Recommendation given:** **A now, B only if a third trip is genuinely bookable.** A costs
nothing, keeps the fieldwork honest, and can be written up in a paragraph. B is the better
question and the worse schedule risk, and the decision between them is a calendar
judgment rather than a methods one. C stays available and loses least if the trips slip —
and per §7 it was always the pre-registered fallback.

**Note on scope.** This measurement makes no claim that the four recovered fieldwork values
are *correct*. They are what the extractor reads from a ticked box. Confirming four values
against four PDFs by eye is a ten-minute job and should happen before any of the options
above is acted on.

**Decision:**
**Reasoning:**
**Date decided:**

---

## Note — this session could not reach either the DCP corpus or GADM
**Date:** 2026-09-12
**This is not a gate.** It is an infrastructure fact about one execution environment,
not a change to any ethics or research decision above.

A session was asked to continue Tasks 3-5 of the build plan: run the parser against the
real 231-document DCP corpus and `tests/test_pdpa.py` against it, load the official
register into Postgres, and report first corpus statistics (recipes per province,
distinct raw ingredient strings, endangerment and acquisition-mode distributions, top
ingredients).

**Outbound network access to `food.culture.go.th` is denied by this session's own
sandbox egress policy** — confirmed both by a direct connection test and by
`scripts/fetch_dcp_food.py`'s own robots.txt preflight, both returning a policy-level
403 before any request reaches the site. This is unrelated to HD-3's `ai-train=no`
question above, which is about whether the *site* permits the fetch — the site was
never reached to ask. `data/raw/dcp_food/` is gitignored by design (rule 8 — the raw
PDFs carry informant PII and must never enter version control), so the 231 documents
fetched on 2026-08-16 are not present in this clone and could not be re-fetched here.
Outbound access to GADM's host (`geodata.ucdavis.edu`, needed by
`scripts/load_geometry.py` for `provinces.geom` and centroids) is denied the same way.
Per this session's own proxy guidance, a policy denial is reported rather than routed
around — no alternate mirror or workaround was attempted for either host.

**Consequence.** No new document was parsed, no row was written to `recipes` beyond
what a future load will add, and no Task 5 number in this note is a fresh measurement.
The corpus-wide distributions already computed on 2026-08-30 and committed to
`data/processed/dcp_field_recovery.json` — `dish_category`, `occasion`, and
`endangerment` value counts across all 231 documents — still stand and can be quoted
from that file; nothing about them changed today.

**What was done instead — machinery only, verified against an empty database rather
than real data.**

- Migration `015_register.sql` adds `recipes.register` (`official | commercial |
  domestic`, NOT NULL) and carries it through `v_recipes_clean`. CLAUDE.md §3 calls this
  "the single most important column in v4" and says it "must not be retrofitted"; it did
  not exist under any name before this migration, and is added now, before any row
  exists in `recipes` anywhere.
- Migration `016_cook_along_log.sql` adds the `cook_along_log` table Bible §7.4 / RQ4
  needs, seeded empty — no cook-along has run.
- `scripts/parse_dcp.py` now writes `register='official'` on every row it loads from the
  DCP corpus, since that corpus is definitionally the state's own register (Bible v4
  §3) — not a judgment call, a fact about the source.
- `Makefile` gained a `db-dump` target wired to the pre-existing `scripts/dump_db.sh`.
- All 16 migrations verified to apply cleanly to an empty database (`sudo -u postgres
  psql` + local PostgreSQL 16 with `postgresql-16-postgis-3` installed, substituting for
  the Docker Compose stack `docker-compose.yml` specifies — this session's container has
  no Docker daemon available. The schema this produces is identical; only the
  provisioning mechanism differs, and it is not a substitute in any environment that can
  run `docker compose up`).
- Full test suite, `ruff check`, and `mypy` all pass unchanged (102 passed, 19 skipped —
  the 19 are exactly the tests gated on the raw corpus being present, per
  `tests/*::raw corpus not present`, i.e. `pytest -rs`).

**What still needs an environment with the right network access.** Running
`scripts/fetch_dcp_food.py` and `scripts/parse_dcp.py` against the live corpus, and then
the Task 5 queries against a freshly loaded database. `.env`'s
`SCRAPER_CONTACT_EMAIL` was set to the researcher's own address for this run, on
explicit confirmation in session — carried here as a fact about what was configured,
not as a decision this file records.

---

## HD-22 — What is a "recipe" on a kapook page?
**Date presented:** 2026-09-12
**Status:** OPEN — `scripts/parse_kapook.py` does not exist. `make ingest` loads
dcp_food only; `make scrape` fetches both sources.

**What depends on it.** Every kapook-derived row in `recipes` — the entire commercial
register (Bible v4 §3's three-way official/commercial/domestic split) has no loader
until this is settled. RQ1, RQ2, and Figure 6 all read `register='commercial'` rows
that cannot exist before this gate closes.

**The finding.** `src/ingest/kapook_page.py` already declines to answer this — its own
docstring: "Deciding how a page maps to rows in `recipes` is an analytical choice about
the unit of observation, not a parsing detail, and it is left to the caller." A page
yields one or more `IngredientSection`s (heading + ingredient lines), and the corpus
contains at least three distinct shapes that look identical structurally (N sections on
one page) but mean different things:

  1. **One dish, one section.** The common case — `title_th` is the dish name, the
     section is its ingredient list. Unambiguous.
  2. **One dish, several sections.** E.g. ส่วนผสม ตัวแป้ง (batter) + ส่วนผสม น้ำจิ้ม
     (dipping sauce) — one recipe, two ingredient groups. Splitting these into two
     `recipes` rows would double-count one dish as two.
  3. **Several dishes, one page (a roundup).** `view159758` carries 46 ingredient
     sections, one per dish in a listicle. Pooling these into one `recipes` row would
     merge 46 unrelated ingredient lists into one fictitious "recipe".

Nothing in the markup distinguishes (2) from (3): both are "a page with N>1 sections",
and telling them apart requires reading whether the section headings name qualifiers of
one dish or names of different dishes — exactly the kind of judgment `measure_labelled_
fraction.py` sidestepped by measuring at the **page** level and saying so explicitly
("the unit of observation is unresolved for this source").

**Options presented:**
  A. **One row per page, always.** Pool every section's items into one ingredient list;
     `dish_name_th` from `title_th`.
     Consequence: cheapest, and correct for shape (1) and (2). Silently wrong for shape
     (3) — a listicle becomes one "recipe" whose ingredient list is the union of up to
     46 unrelated dishes, which would corrupt every ingredient-profile measure RQ1/RQ2
     run on it. No count in hand for how many of the 2,521 usable pages are listicles,
     so the damage is unquantified.
  B. **One row per section, always.** `dish_name_th` from the section heading (falling
     back to `title_th` when the heading is only the ingredient-keyword itself, e.g.
     bare "ส่วนผสม").
     Consequence: correct for shape (3). Wrong for shape (2) — a single dish's batter
     and sauce become two fabricated "recipes", each missing half its own ingredient
     list, which is arguably a worse corruption than A's for exactly the well-structured
     pages that bothered to separate components.
  C. **Load only unambiguous single-section pages (shape 1) now; hold multi-section
     pages out of `recipes` entirely, counted and reported rather than guessed.**
     Consequence: no fabricated unit of observation in either direction. Costs whatever
     fraction of the 2,521 usable pages have more than one section — unmeasured, but
     the fetched corpus and `src/ingest/kapook_page.py` are both already in hand, so
     that fraction is a five-minute count once this option is chosen, not a blocker to
     choosing it.
  D. **Read a sample of multi-section pages by hand and write a rule** (e.g. a heading
     that repeats a known dish-category word or matches a short list of "part" nouns —
     ตัวแป้ง, น้ำจิ้ม, ไส้ — means "same dish, split section"; anything else means "new
     dish").
     Consequence: recovers most of what B and C each give up, but the rule itself is a
     vocabulary-granularity judgment call in the same class as HD-6/HD-9 — how many
     "part" nouns, how confidently a heading must repeat one — and would need its own
     documented inclusion rules the same way `dish_categories` does.

**Recommendation given:** **C now, D as a follow-up if the held-out fraction turns out
large enough to matter.** C is the only option that cannot silently corrupt an
ingredient-profile measurement, and rule 9 (negative results ship) covers reporting
the held-out count plainly rather than treating it as a defect. A and B each get one of
the two multi-section shapes wrong in a way that would not be visible again until RQ1's
numbers looked strange.

**Decision:** **C — load only unambiguous single-section pages now; hold multi-section
pages out of `recipes`, counted rather than guessed.** Recorded from the researcher's
instruction in session, 2026-09-12; the choice is theirs, the transcription is the
agent's.
**Reasoning:**            ← researcher. Still empty, and it is the field the methods
section will quote. The decision is recorded; the argument for it is not.
**Date decided:** 2026-09-12

**What C commits the project to.** `scripts/parse_kapook.py` loads a `recipes` row only
for a page with exactly one `IngredientSection`. Every other fetched page still gets a
`raw_recipes` row (parsed content and all, nothing lost) but no `recipes` row — held out,
not dropped, and re-visitable once shapes (2) and (3) get a rule of their own (D above,
or a fresh option). Options A, B, and D remain available for that follow-up; this
decision closes only "what loads today," not the rest of HD-22.

---

## Note — CLAUDE.md §7.2 states two different dedup Jaccard thresholds
**Date:** 2026-09-12
**This is not a gate.** It is a documentation discrepancy found while building
`src/clean/dedupe.py`'s similarity primitives, not a judgment call this session made.

§7.2's own summary sentence: "deduplicate on ingredient-set Jaccard > **0.9**." Three
lines later, the paragraph headed "Dedupe detail worth keeping from the v2 prompts":
"exact `content_hash` first, then Jaccard > **0.85** on canonical ingredient sets **and**
fuzzy title ratio > 0.8 -> flagged for review." Both read as the same check — an
ingredient-set Jaccard threshold for flagging duplicate recipes — with two different
numbers three lines apart in the same section.

**Not resolved here.** `src/clean/dedupe.py` implements `jaccard_similarity()` and
`title_similarity()` as pure functions with no threshold baked in; callers supply
whichever number they intend. Picking 0.85 or 0.9 as "the" project threshold is the
researcher's call — this note exists so it is made deliberately rather than by whichever
number a future reader (or agent) happens to copy first.

---

## Note — this session could not reach `gdcatalog.go.th` or obtain `thaitastetherapy.csv`
**Date:** 2026-09-12
**This is not a gate.** Like the note above dated the same day, it is an
infrastructure fact about one execution environment, not a change to any ethics or
research decision.

A session was asked to (1) audit `culture.gdcatalog.go.th` and its parent
`gdcatalog.go.th` — robots.txt, licence, a CKAN dataset inventory — and (2) ingest a
manually-downloaded `thaitastetherapy.csv` into the schema, with PDPA stripping of
seven owner/location columns as the ingester's definition of done.

**Neither task's precondition held in this environment.** `WebFetch` on both hosts'
`robots.txt` returned `EGRESS_BLOCKED` — an organisation egress-policy denial, per
`/root/.ccr/README.md`'s own guidance to report such a denial rather than route around
it, not a robots.txt-based finding about the site. This is the same class of denial
the prior note on this date recorded for `food.culture.go.th` and
`geodata.ucdavis.edu`; `gdcatalog.go.th` is a third host blocked the same way. No
robots.txt was read, no licence text was seen, and the catalogue was not enumerated.

Separately, `thaitastetherapy.csv` does not exist anywhere in this session — not at
`data/raw/gdcatalog/` (which the task brief assumed it had already been moved to),
not elsewhere in the container, and a Google Drive search for it
(`mcp__Google_Drive__search_files`, titles containing "thaitastetherapy" or "taste"
+ "therapy") returned no results. `data/raw/` is gitignored, so even a real download
on the researcher's own machine would not appear in a fresh clone or a cloud session —
the same reason the 231 DCP PDFs were absent from the prior note's session. Nothing
was fabricated to stand in for the missing file: no row counts, no region values
beyond the one string the brief itself quotes (`ภาคกลางและตะวันออก`), no ingredient
content.

**What was done instead — machinery only, tested against synthetic fixtures.**

- `src/ingest/gdcatalog.py`: whitelist-selects the six analytical columns
  (`region`, `province`, `foodname`, `originalfoodname`, `otherfoodname`, `material`)
  and never the seven PII ones, by column name rather than by blacklisting the PII
  columns — a schema change that added an eighth personal-data column would still be
  dropped. Classifies `material` into the three shapes the brief documents (clean
  space-separated list, numbered list, prose) and extracts from the first two;
  prose rows are reported unparsed, never guessed at, per the brief's own instruction
  not to run an LLM pass over this field without asking first.
- `src/ingest/pdpa.py`'s shared leak detector (`find_leaks`, already used by
  `tests/test_pdpa.py`'s whole-database scan) gained two classes this source
  specifically introduces: `coordinates` (a bare decimal lat/long pair) and
  `drive_url` (a `drive.google.com` / `docs.google.com` link). Both were already
  redacted by the DCP-forms stripper's `PATTERNS` table; they were missing from the
  broader `LEAK_PATTERNS` table the test suite actually scans with, which is now
  closed for every source, not just this one.
- `tests/test_gdcatalog.py` and `tests/test_gdcatalog_pdpa.py`: format-classification
  and PDPA-guarantee tests built from the brief's own literal examples (the three
  `material` format samples, the three Nan dish names `คั่วไก่` / `ตำถั่วแปป` /
  `แกงสะแล`) and from invented PII fixtures in the `ทดสอบ` ("test") convention
  `tests/test_pdpa.py` already uses — never from the real file, which does not exist
  here to copy from.
- Migration `022_recipes_source_programme.sql`: `recipes.source_programme`
  distinguishes `one_province_one_menu` from `thai_taste_therapy` within the
  `official` register (Task 2c), with a CHECK tying it to `register` and a backfill
  for the DCP rows already loaded. `scripts/parse_dcp.py` now sets it explicitly.
  Verified against an empty database: all 22 migrations apply cleanly
  (`uv run python -m scripts.migrate`, local PostgreSQL 16 +
  `postgresql-16-postgis-3`, substituting for Docker Compose as the prior note
  already established for this environment), and the full test suite passes
  unchanged plus the new tests (158 passed, 19 skipped — the pre-existing
  raw-corpus-gated skips; `ruff check` clean; `mypy` shows no errors beyond the two
  pre-existing `parse_dcp.py` findings this session did not introduce).
- `scripts/parse_gdcatalog.py`: the loader, written to the same shape as
  `scripts/parse_dcp.py` (raw_recipes → redaction_log → recipes → province_attribution,
  no `recipe_ingredients` write — that still waits on HD-6). It refuses to run without
  the CSV in place, and it will additionally fail on the `raw_recipes.source_id`
  foreign key: no `sources` row exists for this source, deliberately — seeding one
  would mean inventing the `robots_ok` and audit-date values migrations 017/018
  transcribed from a completed, dated audit, and no such audit exists yet (see
  `ETHICS.md`'s 2026-09-12 gdcatalog entry). Region is written nowhere but
  `raw_recipes.parsed_json`, unmapped — see the gate immediately below.

**What still needs an environment with the right network access, or the file
supplied directly.** The actual audit (Task 1) and the actual ingestion and its
Task 3 numbers (recipe counts per province/region, extraction success rate by
format, lexicon overlap, the three Nan dishes against fieldwork, the effect on the
corpus-wide labelled fraction) all require either this session's egress policy to
allow `gdcatalog.go.th`, or the CSV to be supplied directly into this environment
(e.g. pasted, or added to a connected Drive this session can read). Whichever the
researcher prefers, nothing above depends on the choice — the parser and its tests
already work.

---

## HD-23 — Region-scheme mapping for `thaitastetherapy.csv`
**Date presented:** 2026-09-12
**Status:** OPEN, and cannot fully proceed to options until the real file is
available — the brief confirms one region string; the other three are not.

**What depends on it.** Whether and how this source's `region` column ever becomes a
canonical `provinces.region4` value anywhere downstream. Nothing currently loads it
there: `scripts/parse_gdcatalog.py` writes the raw string only to
`raw_recipes.parsed_json`, never to `province_attribution.region` — the same field
`scripts/parse_dcp.py` also leaves NULL today, so this is not a new gap, only one now
named for a second source.

**What is known, and what is not.** The brief states the file uses "a four-region
scheme where `ภาคกลางและตะวันออก` merges Central and East" and asks for the exact
set of region values present to be reported before proposing a mapping. This session
has exactly one confirmed value — the one the brief itself quotes — and no way to see
the other three or four, since the file was never available (see the note above).

**A structural observation, not a proposed decision.** `provinces.region4`
(migration 006) is itself a four-way scheme with no separate East value — its CSV
(`data/reference/provinces.csv`) shows exactly `{Central, North, Northeast, South}`,
which means every province this project already calls "Central" already includes
what a five-way scheme would call East. If `thaitastetherapy.csv`'s four Thai labels
turn out to be the ordinary four-region set (ภาคเหนือ / ภาคตะวันออกเฉียงเหนือ or
ภาคอีสาน / ภาคกลางและตะวันออก / ภาคใต้), the merge this source's own label names is
the same merge `region4` already performs — a much smaller decision than HD-1's or
HD-2's, because no folding choice would be introduced that this project has not
already made once. This is offered as a hypothesis the real file can confirm or
contradict, not as the decision itself.

**Options, contingent on that confirmation:**
  A. **Direct name mapping**, once the exact four (or however many) Thai strings are
     seen and, if the structural observation above holds, matched onto `region4`
     one-to-one.
     Consequence: cheapest, and introduces no new judgment call beyond confirming the
     hypothesis above. Wrong only if the file's regions turn out not to align with
     `region4`'s existing Central/East merge — unknowable without the file.
  B. **Leave the CSV's region column unmapped indefinitely**, deriving region only
     from `province` → `provinces.region4` the way every other source implicitly
     would if it populated `province_attribution.region` at all (nothing currently
     does).
     Consequence: sidesteps the mapping question entirely, at the cost of never using
     the source's own stated region as a cross-check against province-derived region
     — a check that might itself surface data-quality issues worth knowing about.
  C. **Store both**: the source's raw region string (already done, in
     `parsed_json`) and a province-derived `region4` value, and compare them.
     Consequence: most informative, costs nothing beyond what B already requires plus
     a join, and turns a mapping decision into a data-quality signal instead.

**Recommendation given:** See the file first. If the structural observation holds, A
costs almost nothing and C is worth doing regardless of which register-mapping
question is chosen — it is nearly free once the province join exists for other
purposes. B is the safe fallback if the file's regions do not align as hypothesised.

**Decision:**
**Reasoning:**
**Date decided:**

---

## Note — `อาหารพื้นถิ่น.csv` (Phetchaburi) also absent; two more hosts blocked
**Date:** 2026-09-12
**This is not a gate.** Same class of infrastructure note as the two entries above
dated the same day.

A session was asked to ingest a second gdcatalog file
(`data/raw/gdcatalog/อาหารพื้นถิ่น.csv`, a 30-row community/village dish-name survey
for Phetchaburi) and to search for sibling files for other provinces, น่าน and
สุรินทร์ specifically.

**The file was not there either.** Not at the expected path, not elsewhere in this
session's container. `data/raw/` is gitignored, so this is the same absence as
`thaitastetherapy.csv`'s, not a new problem — see the first note dated today.

**Task 3's sibling search could not run.** `WebFetch` on `culture.gdcatalog.go.th`,
`gdcatalog.go.th`, and `data.go.th` (a host not tried before today) all returned
`EGRESS_BLOCKED`. Five hosts are now confirmed blocked by this session's own network
policy on this one date: `food.culture.go.th`, `geodata.ucdavis.edu`,
`gdcatalog.go.th`, `culture.gdcatalog.go.th`, and `data.go.th`. No CKAN
`package_search` call reached either catalogue. Whether a sibling file exists for
น่าน or สุรินทร์ — the question with the most value in the brief — is genuinely
unknown, not a negative result.

**The province determination is not a gate, and is recorded rather than deferred.**
The brief names all eight `อำเภอ` values the file is said to carry
(เขาย้อย, บ้านแหลม, ท่ายาง, แก่งกระจาน, เมืองเพชรบุรี, บ้านลาด, ชะอำ, หนองหญ้าปล้อง)
and asks that they be checked against a Thai administrative reference before assuming
they are all Phetchaburi. They are: those eight names are, together, Phetchaburi's
complete and only set of districts — checked against
`data/reference/provinces.csv` (`TH-76`), which is this project's own reference, not
an external fetch. Nothing was guessed. `src/ingest/local_dish_inventory.py`'s
`check_districts_are_phetchaburi` re-runs this check in code on every load — not
trusted from this one-time note — and `scripts/parse_local_dish_inventory.py`
refuses to load anything if a future sibling file's districts do not all resolve.
Per the brief's own instruction, `province_code` is set to Phetchaburi's (`TH-76`)
with a `provenance_note` on every row recording that the value is **inferred from
district names, not stated in the source** — see `ETHICS.md`'s matching entry, which
is where this provenance distinction is meant to survive into the dataset card.

**Two things flagged for later, not decided now, per the brief's own instructions:**

- `ผลิตภัณฑ์เด่น` (mixed food/non-food community products — ขนมหม้อแกง and
  ไข่เค็มสูตรสมุนไพร alongside ผ้าบาติก, กรอบรูป, ปูนปั้นหัวสัตว์) is stored verbatim
  in `local_dish_inventory.featured_products`. No classification is attempted; the
  brief calls this a decision gate explicitly and it is not opened here because
  nobody has asked a question about it yet, only warned against pre-empting one.
- Ingredient words embedded in dish names (ปลาทู, ตาล, ชะคราม) are never extracted.
  Same treatment: flagged as a separate, undecided step per the brief, not attempted.

**What was built regardless — machinery only, tested against synthetic fixtures
built from the brief's own descriptions, never from the real file.**

- `src/ingest/local_dish_inventory.py`: whitelist-keeps the six analytical columns,
  drops `Unnamed:` padding and the two named columns (`ที่อยู่`, `Url รูปภาพ`)
  unconditionally, extracts dish names from mixed `\r\n`/`\n` numbered lists, and
  runs the district-to-province check described above.
- Migration `023_local_dish_inventory.sql`: a new table, not `recipes` — this source
  has no ingredients and cannot join the ingredient-based analysis views. One row per
  (community, dish), `raw_id`-linked back to one `raw_recipes` row per community, per
  rule 1.
- `scripts/parse_local_dish_inventory.py`: the loader (same two preconditions unmet
  as `scripts/parse_gdcatalog.py` — the CSV and a `sources` seed row, deliberately not
  fabricated here) plus `--report`, which runs Task 2's arithmetic against whatever is
  already loaded and prints zero honestly rather than a fabricated count when either
  side has nothing in it.
- `docs/limitations.md` L19: the official-vs-community dish-count comparison uses
  exact string matching across two programmes with different selection criteria and
  plausibly different naming granularity — indicative, not exact, and any mismatch
  undercounts overlap rather than overstating it.
- `tests/test_local_dish_inventory.py`, `tests/test_local_dish_inventory_pdpa.py`:
  built from the brief's literal district list and format description. One real bug
  surfaced and is worth recording here rather than only in the commit history: a
  first draft of the test fixtures typed `อำเภอ` twice by hand and got two different
  Unicode encodings of the same visible string — precomposed SARA AM (U+0E33) once,
  the decomposed NIKHAHIT+SARA AA sequence (U+0E4D U+0E32) once — which silently
  produced two different dict keys instead of one overridden value. NFC normalisation
  does not unify them; Thai does not canonically decompose SARA AM. Fixed by deriving
  every column name the tests use from the module's own constants rather than
  retyping Thai literals a second time. Worth knowing about beyond this one file: any
  future code that compares or hand-types the same Thai string twice can carry the
  same silent mismatch, and it will not raise, just silently not match.

**What still needs an environment with the right network access, or the files
supplied directly.** Task 3's sibling inventory (the highest-value item in the
brief), and Task 2's real arithmetic — both require either this session's egress
policy to admit at least one of the five now-blocked hosts, or the relevant CSVs
supplied into this environment directly.
