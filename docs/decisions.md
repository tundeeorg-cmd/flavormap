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
**Status:** OPEN — `provinces.dialect_group` is NULL for all 77 rows and stays that way
until this is decided.

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
