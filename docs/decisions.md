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

**Addendum, 2026-09-12 — the session report referenced above does not exist.**
Searched exhaustively this session: full-text across every commit on every branch,
including the repo's initial scaffolding commit, which already referenced it as
existing on day one — there is no earlier history to recover it from, and no file
anywhere in the tree contains this rationale. It was very likely a real conversation
that produced the CSV and the two province lists above, but it was never captured as
an artifact.

**Rebuilt from scratch, not recovered, clearly labeled as new:**
[`docs/hd1_dialect_rationale.md`](hd1_dialect_rationale.md). Covers all twelve
Transitional provinces plus the three flagged pairs, drawn from general Thai
dialectology rather than reconstructed memory of the missing report — it may not
match whatever the original said, and was written without live source verification
(no network access this session), so it should be spot-checked before being cited
anywhere final. It surfaces one thing the original list's framing may have missed:
**Satun's case looks conceptually different from the other eleven**, not just
uncertain — its Malay-Muslim population is Southern-Thai-speaking, not
Pattani-Malay-speaking, unlike Pattani/Yala/Narathiwat, which argues the current
Transitional placement may be the wrong shape of answer rather than the wrong
specific label. It also raises a structural question beyond HD-1's original scope:
whether Surin/Si Sa Ket/Buri Ram's documented Northern Khmer and Kuy populations
warrant a seventh category rather than absorption into Isaan_Lao — flagged there for
the researcher, not decided.

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

## HD-23 — Region-scheme mapping across sources (was: `thaitastetherapy.csv` only)
**Date presented:** 2026-09-12
**Revised:** 2026-09-12, same day — a third scheme arrived (`flavormap_food67.csv`
Task 2) before this gate was decided. Extended in place rather than opened as a
second gate, because it is the same underlying question — "what canonical region
value, if any, does a source's own region label map to" — now with a third answer to
reconcile instead of one. The original text is corrected below, not hidden: the
"structural observation" this entry offered as an untested hypothesis on first
presentation is now **confirmed** by food67's evidence, and the option set has
changed shape as a result — see "What food67 adds", below.
**Status:** OPEN. Still cannot fully resolve `thaitastetherapy.csv`'s own four values
(three of four remain unconfirmed — the file is unavailable, see the notes above) but
food67's six values are now known outright, quoted directly in its own brief.

**What depends on it.** Whether and how any source's `region` column becomes a
canonical `provinces.region4` value anywhere downstream. Nothing currently loads one
there: `scripts/parse_gdcatalog.py`, `scripts/parse_food67.py`, and
`scripts/parse_dcp.py` all write only to `raw_recipes.parsed_json`, never to
`province_attribution.region` — not a new gap, one now named across three sources.

**Three schemes now in play, per Task 2 of the food67 brief:**

| Source | Scheme | Values |
|---|---|---|
| `flavormap_food67.csv` | 6-way | ภาคกลาง · ภาคตะวันออกเฉียงเหนือ · ภาคใต้ · ภาคเหนือ · ภาคตะวันตก · ภาคตะวันออก |
| `thaitastetherapy.csv` | 4-way (Central+East merged) | one confirmed: ภาคกลางและตะวันออก. Other three: unconfirmed, file unavailable |
| Wongnai (not yet used) | 3-way, no Central category at all | not sourced — the brief's own claim, unverified against a live Wongnai page in this session (network blocked) |
| `provinces.region4` (this project's own canonical scheme, migration 006) | 4-way | Central · North · Northeast · South — no separate East or West value |

**What food67 confirms that was only a hypothesis before.** The original text of
this entry guessed that `region4`'s Central already absorbs what a finer scheme calls
East, and offered it as untested. food67's own 6-way scheme, quoted directly above,
**proves the finer scheme exists and is in real use by a government source** —
ภาคตะวันออก (East) and ภาคตะวันตก (West) are both named separately from ภาคกลาง
(Central). So the hypothesis was directionally right (region4 does collapse a finer
scheme) but the earlier framing of this as a small, low-cost decision does not survive
contact with a concrete 6-way source: collapsing food67's six values onto `region4`'s
four is a real, irreversible information loss (which of East/West/Central a province
belonged to under the finer scheme cannot be recovered from the coarse one), not a
free relabelling.

**There is no free option, per the brief's own framing of Task 2** — quoted because
it states the trade-off better than a paraphrase would:

> collapsing 6→4 loses information irreversibly, while keeping 6 makes
> thaitastetherapy.csv rows unmappable to ภาคกลาง versus ภาคตะวันออก. There is no
> free option.

Concretely: `thaitastetherapy.csv`'s single confirmed value, ภาคกลางและตะวันออก,
has no counterpart in food67's 6-way scheme at all — it is *by construction* a merge
of two of food67's six values (ภาคกลาง and ภาคตะวันออก) into one label. A scheme
fine enough for food67 cannot represent a thaitastetherapy row without picking one of
its two merged halves for it, and nothing in `thaitastetherapy.csv` says which. A
scheme coarse enough for thaitastetherapy (region4, or a direct copy of its own
four-way scheme) can represent food67 rows only by discarding the Central/East and
(if `provinces.region4` is the target) Central/West distinctions food67's source drew
on purpose.

**Options — revised to name a canonical target explicitly, since "map onto region4"
and "map onto a new project-wide scheme" are no longer obviously the same choice:**
  A. **Canonicalise on `provinces.region4` (4-way, existing).** Every source's region
     column maps down to it; food67's six values collapse to four (Central absorbs
     East and West); thaitastetherapy's four values map close to directly if its
     three unconfirmed values are the expected ones.
     Consequence: zero schema change, keeps every existing figure/query working
     unmodified. Loses food67's East/West distinction permanently for any analysis
     that reads only the canonical column — recoverable only from
     `raw_recipes.parsed_json`'s raw string, never from `province_attribution`.
  B. **Adopt a 6-way canonical scheme project-wide**, matching food67's granularity,
     and derive it for every source from `province` → a province-to-6-region lookup
     (not from each source's own stated region string, which is Wongnai's problem
     below).
     Consequence: no information loss for food67. Costs a new reference column (a
     6-way `provinces.region6` or similar) and a rebuild of every region-faceted
     figure. Still leaves `thaitastetherapy.csv`'s ภาคกลางและตะวันออก rows unable to
     pick a side — the brief's own point — unless resolved by province lookup instead
     of trusting the source's stated region (which is what a province-derived
     approach already does, sidestepping the merged label rather than solving it).
  C. **Store every source's raw region string (already done, per source, in
     `parsed_json`) and derive one canonical value only from `province` — never from
     any source's own stated region column**, at whatever granularity (4-way or
     6-way) is chosen for the canonical scheme.
     Consequence: makes the incompatible source-stated schemes a non-issue for
     anything downstream of `province_attribution`, because nothing downstream reads
     them — they remain available as a per-source data-quality cross-check (does a
     source's stated region agree with what its province implies?) without ever being
     load-bearing. This is what B's own derivation approach already does in practice;
     C just states it as the general rule rather than a per-scheme workaround, and
     applies it whichever granularity (A's four-way or B's six-way) is picked for the
     canonical column itself.
  D. **Wongnai's 3-way scheme (no Central category)** is a fourth incompatible shape
     waiting in the wings, unconfirmed and unsourced this session. Whatever is chosen
     above should be checked against it *before* Wongnai is ever ingested, not
     discovered as a fourth surprise later — flagged here so it is not forgotten,
     not because it needs a decision today.

**Recommendation given:** C, at whichever granularity (A's four-way, matching
existing figures, or B's six-way, matching food67's actual resolution) is chosen for
the canonical column — deriving region from province rather than trusting any
source's own stated region label is the one move that survives all three (four,
counting Wongnai) known schemes without picking a side on food67's East/West split or
thaitastetherapy's Central/East merge. The four-vs-six granularity choice under C is
still a real decision and still hers: six is more faithful to what at least one
government source actually distinguishes; four is zero-cost and matches every figure
already built.

**Decision:** Mechanism: **C — derive the canonical region always from `province`,
never trust a source's own stated region string.** Granularity: **B — six-way**,
matching food67's actual resolution.
**Reasoning:** Recorded from the researcher's instruction in session, 2026-09-12.
Deriving from province survives all four known schemes at once without picking a side
on any source's own merge/split choices; six-way was chosen over four-way because it
is what the only real government source at this resolution (food67) actually
distinguishes, and collapsing it to four loses that distinction irreversibly with no
way to recover it later.
**Date decided:** 2026-09-12

**Implemented same day.** Migration `029_region6.sql` adds `provinces.region6`
(nullable, CHECKed against food67's own six values). `data/reference/provinces.csv`
now carries a `region6` column for all 77 provinces: **48 read directly from
`flavormap_food67.csv`'s own `region_th`**, **29 filled from general Thai
administrative geography this session** (no live source verification possible —
network blocked throughout — flagged the same way `docs/hd1_dialect_rationale.md`
was). `scripts/load_geometry.py` loads `region6` alongside the existing columns for
future real GADM loads; a new `--no-geometry` flag turns the previously ad-hoc
geometry-less stopgap load (used twice now this session alone, since the local
database resets between sessions) into real, tested functionality instead of a
disposable one-off. `scripts/backfill_provinces_reference.py` (new) refreshes
`region4`/`dialect_group`/`border_country`/`region6` on an already-loaded `provinces`
table from the CSV alone, without touching `geom` — the general tool the original
geometry stopgap should have been. `province_attribution.region` (migration 007) is
deliberately **not** backfilled from this column: joining through `province_code` to
`provinces.region6` gives the same answer without the duplication/sync hazard that
column already sat unused because of.

**A real finding surfaced by the implementation, not assumed going in: region4 does
not cleanly nest inside food67's six-way scheme even outside Central.** The original
framing above ("region4 does collapse a finer scheme... Central absorbs East and
West") undersold it. Five provinces carry `region4 = 'North'` but food67 itself places
them elsewhere: **Nakhon Sawan, Uthai Thani, Phitsanulok, and Phichit in ภาคกลาง
(Central)**, and **Tak in ภาคตะวันตก (West)** — confirmed from food67's own real
data, not inferred. Northeast and South, by contrast, have zero such exceptions;
every province in either carries the matching region6 label exactly.
`tests/test_provinces_reference.py::test_region6_north_exceptions_are_exactly_the_confirmed_five`
encodes this as a named, closed list so a future province silently moving in or out
of it is caught rather than absorbed. Worth a sentence in the methods section: the
"lower North" is apparently not northern at all by at least one government source's
own reckoning, which is a genuine, citable finding independent of anything this
project set out to measure.

**Verification.** 29/29 migrations apply from an empty database. 305 tests pass (up
from 301), 19 skipped (pre-existing, unrelated). ruff clean; the two new mypy findings
in `scripts/load_geometry.py` match the same pre-existing `tuple[Any, ...] | None`
indexing pattern already present throughout this codebase, not newly introduced.

**Addendum, 2026-09-12 — `thaitastetherapy.csv`'s remaining three region values are
now confirmed, not just the one.** The real file arrived this session
(`scripts/parse_gdcatalog.py --dry-run`). All four of its distinct raw `region`
strings are now known outright: ภาคกลางและตะวันออก, ภาคตะวันออกเฉียงเหนือ, ภาคเหนือ,
ภาคใต้ — i.e. the North/Northeast/South labels are spelled identically to food67's
six-way scheme, and only Central+East is merged into one label, exactly as the single
previously-confirmed value implied. This does not decide the gate — it removes the
"file unavailable" uncertainty from three of its four rows, nothing more.

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

---

## Note — Task 0: `flavormap_food67.csv` is of undocumented provenance
**Date:** 2026-09-12
**This is the note Task 0c requires**, written regardless of whether the file could
be loaded — provenance is a fact about the file, not about this session's access to
it, and the brief is explicit that an unverified file must not be "laundered into the
corpus" by skipping this step.

**0a — repository search.** `git log --all` (57 commits) and a case-insensitive
`grep` across `*.py`, `*.md`, `*.sql` for "food67" / "food68" / "bookfood" /
"flavormap_food" found **no extraction script, commit, or decision entry** that
produced or mentions `flavormap_food67.csv`. The only trace of "food67" anywhere in
this repository is commit `b8a90d6` (2026-08-16, "DCP corpus enumerated and fetched —
231/231 documents"), whose own commit message says:

> Extension probes, reported not parsed: ... `bookfood67/` (2567 round): 200,
> FlipBuilder shell at `/bookfood67/` and `/index.html`

That is, the *source* this CSV claims to be an extracted version of was located and
identified as a FlipBuilder-rendered digitised flipbook — structurally unlike
`food68`'s 231 discrete per-dish PDFs — and **explicitly not parsed**, by this
project's own record. `flavormap_food67.csv`'s existence is therefore unexplained:
either it was produced by a process outside this repository (by hand, by a different
tool, by a person), or its 2026-08-16 probe result is stale and the volume became
newly extractable since. Neither can be determined from what this repository records.

**0b — spot-verification against source: not possible in this session.**
`WebFetch` on `https://food.culture.go.th/bookfood67/` returned `EGRESS_BLOCKED` — the
same class of denial recorded against this and four other hosts on 2026-09-12 (see
the notes above). Zero of the ten rows the brief asks for could be checked against the
original book pages. **Match rate: 0/10 attempted, 10/10 blocked before a single
comparison could run** — not a measurement of accuracy, a measurement of access.

**0c — the required note, stated plainly:** `flavormap_food67.csv` is of undocumented
provenance. No script, commit, or decision record in this repository explains how it
was produced. It has not been spot-verified against the original 2567 book — 0 of 10
planned rows were checked, because the source could not be reached from this session.
**This file has not been loaded into `recipes`** (see the infrastructure note below —
it is also simply absent from this environment), and nothing in
`scripts/parse_food67.py` or `src/ingest/food67.py` treats it as verified. This note
must reach the dataset card per the brief, and is recorded here so it does not have to
be reconstructed later: whoever eventually loads this file for real should re-run 0b
before trusting it, not assume this note is a stale formality once the CSV is finally
in hand.

## Note — Task 1: 2567 vs 2568 — evidence, without loading either file directly
**Date:** 2026-09-12

**1a.** Two pieces of evidence, both derivable without the file itself:

- **Format.** food68 is 231 discrete per-dish PDFs at a predictable path
  (`food68/{region}/{province_index}/{menu_index}.pdf`, commit `b8a90d6`). food67 is
  one FlipBuilder-rendered volume at `/bookfood67/` — a fundamentally different
  delivery format for what the brief calls "the same programme." Two cohorts of one
  programme sharing a name is consistent with different production choices year to
  year; it does not by itself prove they are the *same* programme with the same
  selection rule.
- **Coverage shape.** food68 is exactly 77 provinces × 3 dishes = 231 — a fixed
  quota, confirmed by construction. food67, per the brief's own counts, is **345 rows
  across 48 of 77 provinces** — roughly 7.2 dishes per covered province on average,
  29 provinces entirely absent, and not a round multiple of any obvious fixed quota.
  If 2567 used the same "3 dishes, every province" rule as 2568, this file does not
  show it: either the file is a partial extract of a larger 2567 volume (consistent
  with 0a's provenance gap — an incomplete, undocumented extraction would explain
  exactly this shape), or the 2567 programme's own selection rule genuinely differed
  from 2568's. **Both readings are live; this repository cannot distinguish them
  without the file and the source.**

**Conclusion for 1a:** the evidence supports "two cohorts of a same-named
programme with at least a different delivery format, and possibly a different
selection rule" — not confidently "consecutive cohorts of one fixed process." This is
exactly why Task 1b's instruction to tag the two years with distinct
`source_programme` values (`one_province_one_menu_2567` /
`_2568`, migration 024) rather than one shared value is the right default regardless
of which reading turns out correct.

**1c — logged to LIMITATIONS.md** (L20) rather than only here, per the brief's own
instruction to do this "before anyone is tempted to write a trend sentence."

**1d — blocked.** Overlap between the years needs both loaded; only machinery for it
exists (`scripts/parse_food67.py --report` computes what it can once the CSV exists;
the equivalent cross-year overlap query is straightforward to add once both `_2567`
and `_2568` rows are actually in `recipes`, and is not built speculatively against
data that does not exist).

## Note — infrastructure: `flavormap_food67.csv` also absent; 0b/Task 3 blocked
**Date:** 2026-09-12
**This is not a gate.** Same class of note as the three infrastructure entries above,
all dated 2026-09-12.

`data/raw/gdcatalog/flavormap_food67.csv` is not present anywhere in this session's
filesystem, consistent with every prior file this task series has referenced. Task 0b
(source spot-verification) and Task 3's downstream numbers (Task 2's real region
counts once mapped, Task 4's actual sara-am/artifact/variant findings against the real
345 rows, Task 5's actual Nan/Surin dish lists) are all blocked on the file, on
network access to `food.culture.go.th`, or both. **What was built regardless —
machinery only, tested against the brief's own literal examples, never against
invented bulk data:**

- `src/ingest/food67.py`: column validation; `|`-split ingredient extraction with
  count validation against the source's own `ingredient_count`; two sara-am
  corruption detectors (one auto-corrected — a bare "น้" with no reason to exist as
  its own word — one report-only per Bible §7.1's explicit warning against a blanket
  regex for the other shape); dish-name artifact detection (report-only, never
  auto-corrected); Khmer-name/Thai-gloss splitting, verified against all five Surin
  names the brief quotes (three split, two don't — `นมเนียล` and
  `อันซอมสะเลอะโดง` carry no parenthetical); ingredient-variant flagging that
  distinguishes a spelling-variant signal (`src.clean.dedupe.title_similarity`, the
  project's existing fuzzy-string measure — reused, not reinvented) from a
  granularity relation (substring containment), verified against all four example
  pairs the brief gives.
- Migration `024_food67_provenance.sql`: provenance columns (`source_dish_id`,
  `book_page`, `pdf_pages`), the never-published prose columns (`method_th`,
  `benefits_th`, `history_th`, `source_info_th`, each with a `COMMENT ON COLUMN`
  recording the restriction on the schema itself), `programme_year`, and a
  `source_programme` vocabulary correction — see the migration's own comment for why
  the pre-existing bare `one_province_one_menu` value is renamed to
  `one_province_one_menu_2568` rather than left standing asymmetrically next to a new
  `_2567` value.
- `scripts/parse_food67.py`: the loader (same two unmet preconditions as every prior
  gdcatalog loader — the file, and a `sources` seed row deliberately not fabricated),
  plus `--report`, which runs the full Task 4 quality pass and works the moment the
  CSV exists, independent of the database gaps.
- Tests (`tests/test_food67.py`, `tests/test_food67_pdpa.py`): 34 tests, built from
  the brief's literal quoted examples (the sara-am string, both dish-name artifacts,
  all five Surin names, all four ingredient-variant pairs) plus Bible §7.1's own
  corruption example, plus invented PII fixtures for the `source_info_th` redaction
  pass (`ทดสอบ` convention). Full suite: 214 passed, 19 skipped (pre-existing
  raw-corpus-gated skips), verified against a real empty database with all 24
  migrations applied — `ruff check` clean, `mypy` shows no findings beyond the same
  pre-existing `tuple | None` indexing pattern already present in every other loader
  script in this codebase.

**What still needs the file, or network access to `food.culture.go.th`.** Task 0b's
spot-verification; the real Task 2/4/5 numbers; Task 1d's year-over-year overlap.

---

## Note — Task 0: the gdcatalog source-catalogue tiering is of undocumented provenance
**Date:** 2026-09-12
**This is the note Task 0b requires.**

**0a — repository search.** No script, commit, or decision entry anywhere in this
repository produced `flavormap_gdcatalog_sources_full.csv`,
`flavormap_gdcatalog_sources_tierA_core.csv`, or assigned their `tier` column. A
case-insensitive search for "tier" across every `.py` and `.md` file in the repository
turns up nothing related — the closest hits are `province_attribution`'s four
*attribution* tiers (an unrelated concept, migration 007) and DCP document parsing.
Nothing in `scripts/`, `docs/source_audit.md`, or `docs/decisions.md` describes
enumerating gdcatalog's catalogue or sorting its rows into tier A/259 and tier
B/1,634.

**0b — recorded per the brief's own instruction.** The tiering is of undocumented
provenance. What it *appears* to be based on, from the numbers alone: 259 of 1,893
(≈13.7%) is a plausible size for a keyword- or metadata-driven first pass (e.g.
matching a province field, a publisher allowlist, or a small set of subject-area
terms) rather than a hand-curated shortlist of that size, which would be an unusual
amount of manual review for a single undocumented step. This is consistent with — and
does not contradict — the brief's own finding that tier A still contains 124 "อาหาร"
titles that are mostly restaurant registries: a mechanical first pass would produce
exactly that kind of noise. **Tier is therefore carried through `source_catalogue` as
provenance only, never as the content filter** — `content_class`
(`src/ingest/source_catalogue.py`) is computed independently, from title and
description text, regardless of which tier a row landed in.

**0c — blocked, machinery ready.** `verify_core_is_subset_of_full` (checks slug
membership and per-column value agreement between the two files, not just row counts)
is built and tested against synthetic fixtures, but has not run against the real
files — both are absent from this environment, see the infrastructure note below.

## Note — infrastructure: both gdcatalog inventory files absent; audit and harvest blocked
**Date:** 2026-09-12
**This is not a gate.** Same class of note as every prior infrastructure entry dated
2026-09-12 in this file.

Neither `flavormap_gdcatalog_sources_full.csv` nor `..._tierA_core.csv` is present in
this session's filesystem or its connected Google Drive — the same absence every
gdcatalog file in this task series has had. Task 2's licence audit and Task 3/4's
harvests are additionally blocked by network access: `food.culture.go.th`,
`culture.gdcatalog.go.th`, `gdcatalog.go.th`, `data.go.th`, and `www.doae.go.th` have
all separately returned `EGRESS_BLOCKED` in this session, and a control fetch to
`www.wikipedia.org` confirms this is a broad session-level policy, not a per-host
finding — see the earlier infrastructure notes and this session's own conversation
for the specific checks.

**A scoping decision this note records rather than defers: no fetch/harvest script
was written for Task 3 or Task 4, even as non-runnable scaffolding.** Every prior
gdcatalog loader in this codebase (`scripts/parse_gdcatalog.py`,
`scripts/parse_local_dish_inventory.py`, `scripts/parse_food67.py`) parses an
*already-downloaded* local file and was safe to write regardless of the source's own
audit status, because parsing a file already on disk is not the act rule 7 gates.
Task 3a and Task 4b are different in kind: they ask for a **fetcher** — HTTP requests
against `*.gdcatalog.go.th`, `data.thaihealth.or.th`, `catalog.qsds.go.th`, and
whatever else Task 2a's domain list turns out to contain — and Task 2's own brief is
explicit: *"Do not fetch from a domain before its entry exists in ETHICS.md."* None of
those domains has one yet, because the audit itself (Task 2b) is exactly what network
access blocks. Writing the fetch code now, unrun, would not violate rule 7 in any way
that executing it would — but it would mean the next reader finds a `fetch_*.py`
targeting five-plus ungoverned hosts sitting in the repo looking ready to run,
which is a worse failure mode than a documented gap. **What was built instead:**

- `src/ingest/source_catalogue.py`: the Task 1b classifier — a first-match-wins
  keyword rule list over the closed vocabulary the brief proposes, with
  `restaurant_registry` checked before any food-related class specifically because
  "ร้านอาหาร" contains "อาหาร" (the brief's own diagnosis of why the keyword is
  noisy) — verified with a test asserting the ordering resolves a title matching both
  keyword sets correctly. `distinct_domains` (Task 2a) and
  `verify_core_is_subset_of_full` (Task 0c) are pure local-file operations, tested
  against synthetic fixtures, and need no network access to run once the CSVs exist.
- Migration `025_source_catalogue.sql`: the tracking table Task 1 specifies —
  `content_class`, `harvest_status`, `rejection_reason`, `assessed_at` — standalone,
  no FK to `sources` or `raw_recipes`, so loading it is not gated on a source audit
  the way every recipe-bearing loader in this codebase is.
- Migration `026_gi_products.sql`: Task 4a's proposed table, product-level only —
  no column for a registrant or applicant name exists, matching Task 4b's instruction
  that registrant lists carry personal data and must never be stored, redacted or
  otherwise.
- `scripts/load_source_catalogue.py`: **not a fetcher** — reads the two CSVs from
  disk only. `--report` runs Task 0c, Task 1's class distribution, and Task 2a's
  domain list, all three of which need only the files, not the database or network.
  Refuses to run without both files present, same as every other loader in this
  codebase.
- 25 new tests (`tests/test_source_catalogue.py`), built from the brief's own five
  confirmed local-food titles, the four named restaurant-certification schemes, and
  the GI/ข้าวหอมมะลิสุรินทร์ example. Full suite verified against a real empty
  database with all 26 migrations applied from scratch: 239 passed, 19 skipped
  (pre-existing raw-corpus-gated skips), ruff and mypy clean.

**What still needs the files, or network access to at least one gdcatalog-family
host.** Task 0c's real subset check; Task 1's real class distribution and Task 2a's
real domain list (the machinery is ready — `load-source-catalogue --report` — only
the files are missing); Task 2b's licence audit; Task 3's three harvests; Task 4's GI
product harvest; Task 5's coverage-correlation analysis, which reads from a populated
`source_catalogue` that does not yet exist. **Task 5b was not written into
LIMITATIONS.md** — the brief asks for an observed finding (does culinary-content
coverage correlate with anything), and there is no observation to log without the
data. Logging a plausible-sounding but unmeasured pattern would be exactly the kind
of thing rule 9's "negative results ship" is not — a result, ships when it is one.

---

## Note — real files supplied directly; every blocked report above now runs for real
**Date:** 2026-09-12
**This is not a gate.** Records that the infrastructure blockers above are partially
resolved (the files exist now; network access to any gdcatalog-family host or
`food.culture.go.th` is still denied, confirmed again this session), and what running
the real numbers actually found — including two real bugs in this session's own
machinery, fixed and tested rather than quietly worked around.

The researcher supplied four CSVs directly (`flavormap_datago_catalog.csv`,
`flavormap_food67.csv`, `flavormap_gdcatalog_sources_full.csv`,
`flavormap_gdcatalog_sources_tierA_core.csv`), placed at `data/raw/gdcatalog/`.
`thaitastetherapy.csv` and `อาหารพื้นถิ่น.csv` were not among them and remain absent.

**food67 — real Task 4 report** (`scripts/parse_food67.py --report`):
345 rows, 48 provinces confirmed exactly. **0 ingredient_count mismatches** — the
`|`-split count agrees with the source's own count on every row. **42 sara-am
corruption instances** (both shapes: bare "น้" and the "consonant + space + า"
shape), all found in `method_th`/`history_th`/`benefits_th`/`ingredients_th` — none
in `dish_name_th`. **31 dish-name artifacts**: the brief's own two named examples
confirmed present verbatim (row 15 `ไก่ทอดมะแขว่น.(ไก่ประดู่หางดำ)`, row 16
`แกงก้าม ขาหมู`), plus 29 more internal-space cases, all listed rather than corrected.
**Correction to the brief's own framing**: "one row has null method_th and one has
null benefits_th" reads as two different rows; the real data has **both nulls on the
same row, 279** — worth noting because it changes what a reader should expect to find
if they go looking for two separate gaps.

**Nan (8) and Surin (9) confirmed exactly** against the brief's counts. Full lists:

- **Nan, all 8**: ขนมอั่ว, ขนมปาด, ขนมดอกซ้อ, น้ำมะไฟจีน, คุกกี้กาแฟน่าน, ลาบปลา,
  ไก่ทอดมะแขว่น.(ไก่ประดู่หางดำ), แกงก้าม ขาหมู — ingredient lists are in the raw CSV,
  not reproduced here; `scripts/parse_food67.py --report` prints them alongside every
  other Task 4 finding.
- **Surin, all 9**: นมเนียล, อังแก๊บบ๊อบ (กบยัดไส้), นมปการันเจก, สันลอเจก (แกงกล้วย),
  จรั้วะโดง (น้ำพริกกะทิ), ขนมมุ, อันซอมสะเลอะโดง (ข้าวต้มมัดใบมะพร้าว), อันซอมกะบ็อง
  (ข้าวต้มด่าง), นมตน็อต (ขนมตาลโบราณ).

**The Khmer-gloss count is 6 of 9 Surin dishes, not 5** — one more than the set the
first task brief quoted (`นมตน็อต (ขนมตาลโบราณ)` also carries the pattern). The other
three Surin names (นมเนียล, นมปการันเจก, ขนมมุ) carry no parenthetical gloss at all,
though two of them share the `นม-` initial syllable with the glossed entries — plausibly
also Khmer-origin, unconfirmed, and a determination this repository has no linguistic
authority to make from a string pattern alone.

**A real finding beyond what either task brief asked for.** The gloss-splitter run
across all 345 rows (not just Surin) surfaces the pattern in other provinces too —
most notably **บุรีรัมย์ (Buriram)**, which borders Surin and sits in the same
lower-Isaan zone: `จรั๊วโดง (น้ำพริกกะทิ)` is close enough to Surin's `จรั้วะโดง` to
plausibly be the same Khmer word transcribed slightly differently, and `อันซอมตรูย`
uses the same `อันซอม-` prefix as two of Surin's dishes. Separately, **ยะลา,
นราธิวาส, ปัตตานี** (the Malay-Muslim deep South) show the same structural
name-plus-gloss shape with names that read as Thai transliterations of Malay/Yawi
(`โรตียาลอ`, `มะตะบะครูเซ็ง`, `ขนมกอและลือเมาะห์`) — a second, separate non-Thai
naming tradition, not the Khmer one. Neither of these is one of the five RQs and
neither is built here — flagged as directly relevant to HD-1's dialect-group
machinery (Isaan_Lao vs. a Khmer-influenced lower-Isaan subgroup; the existing Malay
dialect group) and left for the researcher.

**Two real bugs found by testing against real data, fixed in the same commit as this
note — see the corresponding source files' own history for the fix, recorded here
because a decision log entry that only shows the final state hides that the bug
existed:**

1. `classify_content`'s `agricultural_production` keywords missed bare "ผลผลิต"
   (yield/produce) and "เพาะปลูก" (cultivation) — only the compound
   "ผลผลิตทางการเกษตร" was listed, so the brief's own confirmed top-scoring
   (29-37) rows, e.g. "เนื้อที่เพาะปลูกข้าวโพดเลี้ยงสัตว์ เนื้อที่เก็บเกี่ยว
   ผลผลิต", classified as `irrelevant`. Found by a test asserting the classifier
   catches this exact real title; fixed by adding the bare terms.
2. The GI registrant-vs-product split the brief specifies (two exact phrases,
   "ผู้ขอใช้" / "ผู้ผลิตที่ใช้") catches only 6 of the real 61 GI-classified
   titles across both catalogues. The other ~49 registrant-shaped titles use
   different phrasing entirely — "ผู้ประกอบการที่ขอใช้...", "เกษตรกรที่ได้รับ...",
   "รายชื่อผู้ที่ได้รับ...", "ผู้ปลูก...ที่ขอ..." — all naming a list of *who*,
   the same hazard under different words. `src/ingest/gi_catalogue.py`'s
   `is_registrant_level` widens the check, verified against 12 real titles (the
   brief's own two plus 5 more registrant-shaped ones this session found, plus 6
   real aggregate/product titles that must NOT be flagged) — deliberately
   conservative (an aggregate marker like "จำนวน"/"มูลค่า" must override, or
   "จำนวนผู้ได้รับอนุญาต..." — a COUNT — would itself be wrongly withheld).

**datago_catalog Task 1 — the province bug, quantified for real** (all 3,861 rows,
`src/ingest/thai_province_match.py`):

| Verdict | Count | What it means |
|---|---|---|
| `no_textual_evidence` | 1,983 | valid province name, no support in title/description — **not asserted wrong**, plausibly a structured field this CSV gives no way to see |
| `confirmed_match` | 1,134 | province name appears as a whole word in the title/description |
| `empty` | 674 | no province assigned |
| `invalid_value` | 62 | not one of the 77 real province names at all (junk: "แปลง", "ศูนย์เมล็ดพันธ์ข้าว", "ประเทศไทย", ...) |
| `trap_mismatch` | 8 | **confirmed wrong** — a known substring trap explains the value |

**The confirmed-wrong count is 8, not "most of 3,861."** All 8 are the two traps the
brief named: 7 "แพร่" rows tripped by "เผยแพร่" (published) inside a title, and the
1 "น่าน" row tripped by "น่านน้ำ" (territorial waters) — the brief's own headline
example, present verbatim: *"เรือประมงนอกน่านน้ำ และเรือขนถ่ายสัตว์น้ำนอกน่านน้ำ..."*
assigned `province='น่าน'`. **62 more rows carry an outright invalid value** (not a
real province name), which is a different, simpler kind of damage — a leaked header
fragment or a non-geographic label, not a substring trap. The large
`no_textual_evidence` bucket (1,983, over half the file) is **not counted as damage**
— see Task 1c's framing below for why conflating it with the 8 confirmed errors would
overclaim.

Option (b) — PyThaiNLP `newmm` whole-token matching — is the matcher used for all of
the above, verified empirically (not assumed) against both named traps before being
trusted: `word_tokenize('เรือประมงนอกน่านน้ำ...')` yields `'น่านน้ำ'` as one token,
never `'น่าน'` alone; `word_tokenize('เผยแพร่ข้อมูล')` yields `'เผยแพร่'` as one
token, never `'แพร่'` alone. Option (c), an explicit blocklist, is implemented as a
defense-in-depth cross-check, not the primary method — it is incomplete by
construction (it only catches traps someone has already found; `เลย`, "at all", is
flagged in the module itself as a name this approach cannot safely cover at all).
Option (a) — trust a structured field where the source provides one — could not be
implemented from this CSV alone: nothing in it distinguishes a `province` value that
came from data.go.th's own structured metadata from one a text-matching step
backfilled, which is itself part of why the `no_textual_evidence` bucket cannot be
asserted wrong.

**Task 1d — `flavormap_gdcatalog_sources_full.csv` is NOT contaminated the same
way.** Re-running the identical check against its `province_th` column: **exactly 77
distinct values, all of them real province names, zero `invalid_value`, zero
`trap_mismatch`.** This is a materially cleaner situation than datago's, consistent
with gdcatalog's own per-province subdomain structure
(`{province}.gdcatalog.go.th`) plausibly providing a genuinely structured province
field rather than one derived from title text. No correction to any previously
reported number from this file is needed.

**Task 2 — `relevance_score` and `flavormap_layer`: no script found, same pattern as
every other undocumented-provenance finding this project has made.** A repository-wide
search for "relevance_score", "flavormap_layer", "datago" found nothing before this
session's own new files. The inversion is confirmed, not assumed: `3_ingredient_agri`
(crop/livestock yield statistics) scores mean 11.2, max 37; `1_dish_culture` (the
layer that should matter most here) scores mean 6.7, max 13 — **every row in the
confirmed top-scoring band (29-37) checked by hand is crop-yield statistics**, none of
it food-culture content. `score_note` (`src/ingest/datago_catalog.py`'s `SCORE_NOTE`
constant) is attached to every row rather than the column being dropped, per Task 2b.

**Task 2c — reclassified by content, not layer, confirming the brief's own
diagnosis.** `1_dish_culture`'s 270 rows do contain the household-fuel and
economic-survey noise the brief names verbatim
("ร้อยละของครัวเรือนที่มีการใช้เชื้อเพลิงแข็งในการประกอบอาหาร") — these classify
`irrelevant` under the shared content classifier
(`src/ingest/source_catalogue.py`), never inheriting a food-culture class just from
their layer. One real, small (2 of 3,861 rows) classifier false-positive is worth
recording rather than silently living with: two household-technology-survey titles
picked up `cultural_heritage` via the **description-fallback**, because a shared
policy-boilerplate description sentence
("...โดยอาศัยภูมิปัญญามาเสริมสร้างนวัตกรรม...") happens to contain "ภูมิปัญญา" even
though the dataset itself has nothing to do with cultural heritage. Not patched with
more keyword engineering (that is the exact whack-a-mole pattern Bible §7.1 already
warns against for a different extraction problem) — recorded as a known, small
limitation of description-fallback matching instead.

**Full reclassified `content_class` distribution, both catalogues** (mechanical,
first-match-wins, per `src/ingest/source_catalogue.py`):

| content_class | gdcatalog (1,893) | datago (3,861) |
|---|---:|---:|
| irrelevant | 1,213 | 1,997 |
| agricultural_production | 435 | 1,555 |
| restaurant_registry | 116 | 157 |
| gi_registration | 51 | 24 |
| tourism | 49 | 67 |
| cultural_heritage | 25 | 56 |
| local_dish_inventory | 4 | 5 |

**Task 3 — dedup, real numbers** (`src/ingest/catalogue_merge.py`,
`build_merge_report`, counted across the full combined sequence — including any
row that duplicates an *earlier row within the same catalogue*, not only
cross-catalogue pairs, which is why these numbers run higher than a naive
cross-catalogue-only set intersection):

- `url_duplicate_pairs`: **1,045**
- `title_org_duplicate_pairs` (additional, found only by title+publisher after the
  URL pass): **303**
- `same_title_different_resource` (reported separately, never folded into the
  duplicate count): **962**
- **`combined_distinct_total`: 4,406** of 5,754 raw rows (1,893 + 3,861)

A simpler cross-catalogue-only check confirms the brief's own headline number
exactly: **1,124 distinct `dataset_title_th` values appear in both files.** Of those,
866 also share a `resource_url` (true duplicates by the brief's own two-stage
definition) and 258 do not (same-title-different-resource). `title_org` (publisher
name) agreement is much narrower than title agreement alone — only 146 of the 1,124
title-matching pairs also agree on publisher/organisation name — which says the two
catalogues format the same real organisation's name differently often enough that
`title_org` alone would under-count the overlap; `resource_url` first, exactly as the
brief specifies, is why the real matcher does not rely on `title_org` as its primary
signal.

**All 5,754 rows loaded into `source_catalogue` for real**, `catalogue_source`
distinguishing the two, `duplicate_of_catalogue_id` resolved post-insert via
`row_hash` (1,363 rows flagged as a duplicate of an earlier row). Which side of a
flagged pair is authoritative is not decided here — same as HD-12's own scope for
recipe-level dedup.

**Task 4 — the shortlist, found and reported, not fetched** (`food.culture.go.th`
and every `*.gdcatalog.go.th` subdomain returned `EGRESS_BLOCKED` again this
session; harvesting stays fully blocked):

- **`gisich.csv`** (Task 4a) — confirmed present in both catalogues, identical
  resource URL: `https://culture.gdcatalog.go.th/dataset/.../download/gisich.csv`,
  publisher กรมส่งเสริมวัฒนธรรม (the same department behind the 231-PDF programme
  and `food67`), `dataset_slug=gdpublish-ich-51-02`, 1 resource, CSV,
  last_modified 2024-09-02. Description confirms it is a national-level rollup of
  both nationally- and provincially-listed ICH items
  ("...ระดับจังหวัดในระดับภาพรวมของประเทศ ทั้งที่ขึ้นบัญชี...ระดับชาติ..."). Whether
  it carries a food/อาหาร category, and whether any entries correspond to dishes
  already in the official register, **cannot be answered without fetching it** — the
  one thing this session could not do.
- **มรดกภูมิปัญญาอาหาร [สมุทรสงคราม]** (Task 4b) — found, datago only. CSV, 3
  resources, resource URL ends `localfood.csv`, description states plainly
  "อาหารพื้นบ้านในจังหวัดสมุทรสงคราม ที่มีการบันทึกไว้" (folk food in Samut
  Songkhram, recorded) — reads exactly like a local dish inventory despite
  classifying `cultural_heritage` under the mechanical keyword rules (its title has
  no exact `local_dish_inventory` phrase; a case the module's own docstring already
  flags this classifier can miss). Whether it carries ingredients is unknown without
  fetching.
- **Provincial ICH — นนทบุรี found, ศรีสะเกษ and อุตรดิตถ์ not found.**
  `บัญชีมรดกภูมิปัญญาทางวัฒนธรรมของจังหวัดนนทบุรี` exists (datago only; formats
  `PDF|API`, 2 resources, one a bare `untitled.pdf`, and its `dataset_page_url`
  itself embeds a Google Drive folder link — flagged, not followed, per rule 8's
  standing treatment of third-party Drive links throughout this project). **Neither
  catalogue contains a dedicated ศรีสะเกษ or อุตรดิตถ์ ICH registry** — the 7 rows
  either province name appears in are agricultural statistics, market-price bulletins,
  or household-debt surveys, none of them ICH-shaped. The brief's own priority
  reasoning for ศรีสะเกษ (borders Surin, same lower-Isaan Khmer zone) stands as a
  reason to *look for* one, not as evidence one exists — reported as a genuine
  negative result, not a near-miss forced into a match.

**Task 4c/earlier task — GI products for Nan and Surin, now concrete.** Nan: **zero**
GI-classified rows in either catalogue. Surin: **4 GI dataset titles across both
catalogues, and all 4 are registrant-level** (ผู้ขอใช้/ผู้ผลิตที่ใช้ for
ข้าวหอมมะลิสุรินทร์ and ข้าวหอมมะลิทุ่งกุลาร้องไห้ — 2 products × 2 list-types) —
**none of the 4 may ever be fetched**, per Task 4b. The 2 product names themselves
are not personal data and are safely known from dataset-title metadata alone, with no
file fetch required: `gi_products` now carries both
(ข้าวหอมมะลิสุรินทร์, ข้าวหอมมะลิทุ่งกุลาร้องไห้; province TH-32; category ข้าว),
`registration_status` left NULL because applicant-vs-certified is not determinable
from a title.

**Task 5 — Nan and Surin, corrected counts, both catalogues.** Nan: datago 14 raw →
**13 after removing the one confirmed trap error** (the fishing-vessel row); gdcatalog
8. Combined **0 rows classify `local_dish_inventory`, `gi_registration`, or
`cultural_heritage` in either catalogue, for Nan, at any stage of correction.** Surin:
datago 80 (no trap corrections needed — Surin carried none), gdcatalog 30; **0 rows
classify `local_dish_inventory` or `cultural_heritage`** in either catalogue; GI as
reported above. **Confirms the brief's own framing without qualification: neither
fieldwork province has dish-level open data in either national catalogue.** Logged to
LIMITATIONS.md (L21) per Task 5b.

**A stopgap taken to unblock `gi_products`' foreign key, flagged so it is never
mistaken for real geometry data.** `provinces` was empty in this session's database
(no prior session in this environment had populated it — `scripts/load_geometry.py`
needs GADM data from `geodata.ucdavis.edu`, also `EGRESS_BLOCKED` this session, same
as every other host tried). The 77 rows were loaded directly from
`data/reference/provinces.csv` (code, name, region4, dialect_group) with
**`centroid_lat`/`centroid_lon` set to a placeholder `0, 0`** (a real point in the
Gulf of Guinea, not Thailand — chosen precisely because it cannot be mistaken for a
plausible real value) and `geom` left NULL. **Nothing that reads centroid or geometry
should trust this table as-is** — Figure 1/2's geographic work and any distance
calculation need `scripts/load_geometry.py` re-run against real GADM data first.
`border_country` was left NULL for all 77 rows too (not sourced from the CSV's
pipe-delimited column in this stopgap load) — HD-2's decision is unaffected, since
the source-of-truth CSV itself is untouched; only this session's database copy is
incomplete.

**Task 5c, logged and not built, per the brief's own instruction.** Surin's 28
(datago) / 7 (gdcatalog) `agricultural_production`-classified rows are not
inspected further here. A possible supporting analysis — what Surin's agricultural
data says it grows, set against what the official register says Surin cooks — is
flagged as available if the researcher wants it later. It is not one of the five
RQs and no code toward it exists.

---

## `flavormap_oae_production.csv` — loaded as `crop_production`, Tasks 1–5
**Date:** 2026-09-12
**Scope note.** This is supporting data (the brief's own framing): it answers none of
the five research questions and nothing here promotes it to one. Kept deliberately
small — one table, one loader, one report, this entry — per the brief's own "if this
task starts expanding, it has drifted."

**Task 1b — province column is clean.** 77 distinct values, **all 77 match
`data/reference/provinces.csv` exactly, zero invalid** (`scripts/load_crop_production.py
--report`). Confirmed, not assumed — this is a structured source field, unlike
`flavormap_datago_catalog.csv`'s free-text-derived `province` column (L21), which is
exactly the contrast the brief asked to check for.

**Task 1c — region_th is an exact match with food67.** Same six values, same
spelling, confirmed by set comparison: ภาคกลาง, ภาคตะวันตก, ภาคตะวันออก,
ภาคตะวันออกเฉียงเหนือ, ภาคเหนือ, ภาคใต้. One fewer mapping problem, as the brief said —
though note this doesn't touch HD-23 (the region-scheme canonicalisation gate),
which is about mapping these onto `provinces.region4`, still open.

**Task 1d — zero PDPA exposure, confirmed by inspection.** All 17 source columns
(province_th, region_th, commodity_th, subcommodity_th, year_be/ce, five area
columns, production/production_unit, yield_per_rai/yield_unit/yield_basis,
source_dataset) are geographic or numeric. No name, address, or contact field exists.
No redaction step was added — there is nothing to redact, and adding one would be
ceremony over a real absence of risk, per the brief's own instruction.

**Task 2a — the unit trap, with real numbers.** `production_unit` takes exactly two
values: **ตัน** (tonnes, every commodity except one) and **ผล** (individual fruits,
มะพร้าวผลแก่ only). `yield_unit` correspondingly: กิโลกรัมต่อไร่ / ผลต่อไร่.
`yield_basis` takes three values: harvested (7 annual-crop commodities), bearing
(coffee, coconut, pepper), tapped (rubber only) — never "and others" as loosely
described, exactly three. `check_unit_consistency()` (`src/ingest/oae_production.py`,
tested) asserts one unit per commodity and found **zero violations** in the real
482 rows. Migration 028 documents the hazard in-schema; no aggregate view exists on
this table for the same reason.

**Task 2b — area column validity by commodity, confirmed from real data, not
guessed:**

| Growth habit | Commodities | Valid area columns | yield_basis |
|---|---|---|---|
| Annual crop | ข้าว, ข้าวโพด, มันฝรั่ง, กระเทียม, หอมแดง, สับปะรด, หอมหัวใหญ่ | planted_area_rai, harvested_area_rai | harvested |
| Perennial | กาแฟ, มะพร้าวผลแก่, พริกไทย | standing_area_rai, bearing_area_rai | bearing |
| Rubber (its own case) | ยางพารา | standing_area_rai, tapped_area_rai | tapped |

Every row populates exactly the two area columns its growth habit uses and leaves the
other three blank — not one row mixes the pattern. The blanks are structural, not
missing data; nothing was imputed into them.

**Task 3a — proposed commodity → lexicon mapping, HD-24, not applied.**

| Commodity (`crop_production`) | Proposed lexicon target | Status |
|---|---|---|
| กระเทียม | กระเทียม | Direct — same word, no inference |
| หอมแดง | หอมแดง | Direct — same word, no inference |
| มะพร้าวผลแก่ | กะทิ | **Inference, flagged.** The commodity is the whole fruit; the lexicon target is a derived product (coconut milk). Not the same thing, and the mapping assumes a province that grows the fruit is a reasonable proxy for a province with coconut-milk access — untested here |
| พริกไทย | พริกไทย | Direct — same word, no inference |
| ข้าว | *(left unmapped, per the brief)* | ข้าวนาปี/ข้าวนาปรัง are planting seasons, not the ข้าวเหนียว/ข้าวหอมมะลิ variety distinction that matters culinarily. Inferring variety from season, region, or yield was not attempted |
| ยางพารา, มันฝรั่ง, สับปะรด, ข้าวโพด, กาแฟ, หอมหัวใหญ่ | *(left unmapped)* | Not food-lexicon-relevant (rubber) or not confirmed to map cleanly without more work than this session's scope allows |

**Not applied** — this table is a proposal for the researcher's decision, per Bible
§15's canonical-vocabulary granularity gate. No `ingredient_aliases` or
`canonical_ingredients` row was touched.

**Decision:** The three direct matches (กระเทียม→กระเทียม, หอมแดง→หอมแดง,
พริกไทย→พริกไทย) are **approved**. The coconut mapping (มะพร้าวผลแก่→กะทิ) is
**accepted, flagged as approximate** — every downstream use of it (figure, table,
lexicon note) must carry an explicit caveat that fruit production is not the same
measurement as coconut-milk usage. ข้าว and the six remaining commodities
(ยางพารา, มันฝรั่ง, สับปะรด, ข้าวโพด, กาแฟ, หอมหัวใหญ่) stay unmapped, as proposed.
**Reasoning:** The three direct matches carry no inference — same word on both sides
of the OAE/lexicon boundary. The coconut mapping is weaker: Task 4's own numbers show
the two biggest producers (สุราษฎร์ธานี, นครศรีธรรมราช) had the largest rank gaps
against dish-appearance frequency in food67, mild evidence the proxy is imperfect —
but n is too thin (27 provinces) to call it disproof, and dropping the mapping
entirely would discard the only supporting-figure signal this commodity offers. The
caveat requirement keeps the approximation from being read as equivalent-strength
evidence to the three direct matches anywhere it is used later, including once HD-6
authors the real canonical lexicon.
**Date decided:** 2026-09-12
**Still not applied to any table** — `canonical_ingredients` remains empty pending
HD-6; this decision only settles how the mapping is framed in this note and in any
future lexicon-authoring pass, not a database write made today.

**Task 3b — lexicon overlap, the real count.** food67's `ingredients_th` column
splits into **1,171 distinct raw strings** (`src/ingest/food67.py::split_ingredients`,
confirmed — this is the same figure the brief itself quotes, independently
reproduced here rather than trusted). A naive substring-containment match against the
four mappable commodities' targets returned 214/1171 (18.3%) — rejected as
overcounting, the same class of false positive `thai_province_match.py` was built to
avoid for provinces (e.g. "containing กะทิ" catches น้ำตาลมะพร้าว, a compound
false positive of a different kind). A tighter starts-with match against each
proposed lexicon target (กระเทียม, หอมแดง, กะทิ, พริกไทย) gives:

| Target | Raw strings starting with it |
|---|---|
| กระเทียม | 20 |
| หอมแดง | 17 |
| กะทิ | 15 (plus 47 more matching น้ำกะทิ/หัวกะทิ — legitimate coconut-milk forms a strict prefix match misses) |
| พริกไทย | 10 |
| **Union (no double count)** | **62 / 1,171 = 5.3%** |

**A low overlap, as expected, and the finding rather than a failure** — of 1,171
distinct raw ingredient strings in the official register, only ~5% (perhaps ~9% if
the กะทิ-variant forms are folded in) have any production counterpart in this file at
all. The other 10 commodities and the vast majority of food67's ingredient
vocabulary (herbs, proteins, sauces, prepared condiments) have no production-side
cross-reference in this source.

**Task 4 — production rank vs. dish-appearance frequency, logged as a possible
supporting figure, not built into a research question, per the brief's own
instruction.**

**Year mismatch, found and flagged rather than silently resolved.** The brief said
"use 2567 for the comparison." **2567 does not exist in the source for three of the
four target commodities** — กระเทียม, หอมแดง, and มะพร้าวผลแก่ carry **only 2568**
rows (18/19/43 rows respectively); only ข้าวโพด, ข้าว, ยางพารา, and สับปะรด have 2567
data. This is a real data-availability fact, not a choice — the comparison below uses
**2568**, the only year that exists for these three commodities, stated explicitly
rather than silently substituted. food67 remains the 2567 programme; the one-year
offset between the two sides of every comparison below should be read with that in
mind.

n is thin throughout (12, 12, and 27 provinces respectively, of 77) — per the brief's
own 4b caution, **no correlation coefficient or p-value is reported**, only counts
and named outliers.

- **กระเทียม** (12 provinces with both 2568 production and ≥1 food67 dish).
  Outliers: **ชัยภูมิ** ranks 9th of 12 in production but **1st** in dish-share
  (3 of 6 dishes) — cooks with it far more than its production rank suggests.
  **ลำปาง** (2nd producer) and **เชียงใหม่** (1st producer) both rank low in
  dish-share (9th and 7th) — grow a lot, appear rarely in the official register.
- **หอมแดง** (12 provinces). **เชียงใหม่** (2nd producer) and **ศรีสะเกษ** (**1st**
  producer, 83,996 tonnes) both show **zero** food67 dishes naming it — the single
  largest producer in the sample has no register-visible use at all. **ยโสธร** and
  **ชัยภูมิ** cook with it far more than their mid-table production rank suggests.
- **มะพร้าว/กะทิ** (27 provinces, the largest n of the three). **สุราษฎร์ธานี**
  (3rd-largest producer, ~49 million fruits) ranks only 22nd of 27 in dish-share —
  the biggest gap found (19 rank positions). **นครศรีธรรมราช** (2nd producer) shows
  a similar pattern (13-position gap). Conversely **นนทบุรี** and **นครปฐม** — small
  producers — rank near the top in dish-share.

Full per-province tables (production, dish counts, ranks) are reproducible from the
same script used to compute this; not copied in full here to keep this entry
readable. Given n and the year mismatch, **none of this is evidence of anything on
its own** — consistent with the brief's own framing, and the finding stands as
"production rank and cooking-frequency rank visibly diverge for the biggest
producers in two of three ingredients," offered as a supporting-figure candidate
only.

**Task 5 — Nan and Surin, all 7 rows each, in full** (`crop_production`, both years):

| Province | Commodity | Subcommodity | Year | Production | Unit |
|---|---|---|---|---|---|
| น่าน | กาแฟ | กาแฟ | 2568 | 936 | ตัน |
| น่าน | ข้าว | ข้าวนาปี | 2567 | 164,965 | ตัน |
| น่าน | ยางพารา | ยางพารา | 2567 | 51,774 | ตัน |
| น่าน | กระเทียม | กระเทียม | 2568 | 150 | ตัน |
| น่าน | ข้าว | ข้าวนาปรัง | 2568 | 8,357 | ตัน |
| น่าน | หอมแดง | หอมแดง | 2568 | 28 | ตัน |
| น่าน | ข้าวโพด | ข้าวโพดหวาน | 2567 | 7,445 | ตัน |
| สุรินทร์ | ข้าว | ข้าวนาปี | 2567 | 1,189,602 | ตัน |
| สุรินทร์ | มะพร้าวผลแก่ | มะพร้าวผลแก่ | 2568 | 3,172 | ผล |
| สุรินทร์ | ยางพารา | ยางพารา | 2567 | 49,309 | ตัน |
| สุรินทร์ | กระเทียม | กระเทียม | 2568 | 26 | ตัน |
| สุรินทร์ | ข้าว | ข้าวนาปรัง | 2568 | 56,798 | ตัน |
| สุรินทร์ | หอมแดง | หอมแดง | 2568 | 123 | ตัน |
| สุรินทร์ | ข้าวโพด | ข้าวโพดหวาน | 2567 | 1,926 | ตัน |

Confirms the brief's own headline: Surin's wet-season rice (1.19M tonnes) dwarfs
Nan's (165K tonnes) — roughly 7×. Both grow garlic and shallot in small, comparable
quantities (26–150 tonnes each). Nan is the only one of the two growing coffee; Surin
the only one of the two with any coconut recorded. A real difference in agricultural
character, useful context before the trips, proving nothing on its own.

**Verification.** 28/28 migrations apply cleanly from an empty database
(`make db-reset` equivalent). 301 tests pass (up from 292 — 12 new tests in
`tests/test_oae_production.py`), 19 skipped (pre-existing, unrelated). ruff and mypy
clean on all new files. Real load: 482/482 rows inserted into `crop_production`,
0 rejected.

---

## Note — `thaitastetherapy.csv` and `อาหารพื้นถิ่น.csv` real reports, finally
**Date:** 2026-09-12
**This is not a gate.** Both files arrived this session. Loading into `recipes` /
`local_dish_inventory` remains blocked exactly as before — no dated `ETHICS.md` audit
for `gdcatalog.go.th` exists yet, so no `sources` FK row was seeded, per rule 7 and
this project's standing refusal to invent an audit. Only the parse/report layer
(`--dry-run`, which touches no database) is unblocked by having the real files. The
original Round-1 and Round-2 briefs' "report back" questions are answered below.

**`thaitastetherapy.csv` (`scripts/parse_gdcatalog.py --dry-run`).** 52 rows, 21
provinces, 4 raw region strings (see the HD-23 addendum above — this run is what
produced it). Ingredient extraction: **clean_list 22, numbered_list 29 (both fully
auto-extracted), prose 1** — 51/52 = 98.1% success, the one prose row
(แกงเลียง, อุตรดิตถ์) held out for hand review rather than force-parsed. Per-province
counts range from ปทุมธานี's 7 down to eighteen provinces with 1. **Nan: 3 dishes**
(คั่วไก่, ตำถั่วแปป, แกงสะแล). **Dish-name overlap with food67's 2567 register: 2 of
52** (แกงบอน/ปทุมธานี, กะลอจี๊/ระนอง) — exact-string match, so a lower bound per L19's
own caveat, but a low number consistent with this project's broader RQ1/RQ3 finding
that different registers rarely name the same dish the same way.

**`อาหารพื้นถิ่น.csv` (`scripts/parse_local_dish_inventory.py --dry-run`).** 30
communities, **150 dish-name mentions, 144 distinct**, all 30 communities'
districts confirmed against `PHETCHABURI_DISTRICTS` (8 distinct districts seen,
zero districts outside the expected set) — the province inference holds cleanly.
Zero empty-menu rows. **Overlap with food67's 3 official Phetchaburi dishes
(ข้าวเหนียวไข่แมงดาทะเลเชื่อม, น้ำพริกลำแพน, ผัดไอ้คุ่ย): zero**, exact-string match —
144 community-named dishes, none of which match the state's three-dish shortlist by
name. Phetchaburi is not a fieldwork province, so this is not RQ3 evidence in the
strict sense, but it is the same shape of finding RQ3 predicts, found incidentally in
a province nobody was looking at for that purpose.

---

## Note — `gisich.csv` received directly; characterized, not built
**Date:** 2026-09-12
**Not a gate, not a task.** The researcher's message asking for network access to
`gisich.csv` was answered by direct upload rather than a successful fetch (network
egress to `culture.gdcatalog.go.th` is still `EGRESS_BLOCKED`, re-confirmed this
session, no change from every earlier test). The file is now at
`data/raw/gdcatalog/gisich.csv`. No task brief scopes what to do with it, and this
session's live brief (`flavormap_oae_production.csv`) is explicit about staying
cheap — so this is a characterization only: row counts and column meaning, enough to
know what it is, no migration, no loader, no test.

**What it is.** 4,718 rows — Thailand's **intangible cultural heritage inventory**
(มรดกภูมิปัญญาทางวัฒนธรรม), not a recipe or dish-name source. Columns: `id`, `Name`,
six binary domain flags (`Literature`, `Arts`, `Festival`, `Knowledge`, `Craft`,
`Folk games`), `TH_Year`/`PV_Year` (registration years, Thai/provincial), a `Region`
and `Province` pair, a free-text `Status` field, a `Practice` location description,
and `Latitude`/`Longitude`. All 77 provinces present; Nan carries 54 rows, Surin 49.

**Why this might matter more than a routine characterization — flagged, not acted
on.** `Status` is a **real endangerment field** with 9 distinct values, headlined by
มีการปฏิบัติอย่างแพร่หลาย ("widely practiced", 3,080 rows) and
เสี่ยงต่อการสูญหายต้องได้รับการส่งเสริมและรักษาอย่างเร่งด่วน ("at risk, urgent
preservation needed", 1,372 rows) — real variation, not the single-value wall RQ5's
open gate currently hits with the DCP corpus's checkbox extraction (four of six
Nan/Surin documents carrying endangerment, all four identical, per §4's OPEN GATE and
`docs/checkbox_extraction.md`). A rough keyword scan (อาหาร/กิน/สูตร/ต้ม/แกง/น้ำพริก/
ขนม/ปรุง/ข้าว/ครัว in `Name`) finds **328 rows** that look food-adjacent — recipes,
techniques, or food-related customs sit inside the `Knowledge`/`Festival` domains
alongside dance, textile, and ritual entries this file also carries.

**This is not a recommendation to fold it into RQ5.** It is a fact worth having in
view given that gate is explicitly stuck: this file has variation where the DCP
sample does not, covers both fieldwork provinces at real scale (54 and 49 rows), and
carries coordinates. It is also not a food-specific source — most of its 4,718 rows
are unrelated cultural domains, its `Status` field's semantics (self-reported by
whichever community submitted the entry, unclear against what rubric) are unverified,
and no PDPA check beyond a column-name glance has been done (the visible columns
carry no name/address/contact field, but that is an inspection, not the audit this
project's own PDPA rule requires before any load). If this is worth pursuing, it
needs its own scoped task brief — Bible §4's RQ5 gate is a research-question
decision, not something to resolve inside a "keep it cheap" supporting-data session.
