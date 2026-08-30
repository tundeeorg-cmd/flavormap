# Blocking item 3 — the Wingdings checkbox go/no-go

**Measured 2026-08-30 on all 231 DCP documents.** Regenerate every number below with
`uv run python -m scripts.measure_dcp_fields`; the machine-readable form is written to
`data/processed/dcp_field_recovery.json`.

Bible §23 item 3 is the go/no-go on RQ5, and §22 lists "endangerment checkbox
unextractable" as a HIGH risk with RQ5 dying alongside it. §5 says why: the forms carry
no AcroForm and no annotations, so the checkboxes are Wingdings glyphs drawn as text.
Both `dish_category` and `endangerment` depend on them.

## The answer, in two parts

**The extraction works.** Endangerment is recovered on 157 of 231 documents (68.0%), and
the ceiling — every document where a §3 box is ticked at all — is 160 (69.3%). The
extractor is within 1.3 points of the most any parser could get from this corpus.

**RQ5 still has no data, for an unrelated reason.** The question compares official
endangerment against cooks in Nan and Surin *on the same dishes*. The state selected three
dishes per province, so RQ5's sample is six documents, not 231:

| Province | Document | Endangerment | Dish |
|---|---|---|---|
| Nan | `north_6_1.pdf` | `transmitted` | แกงส้มเมืองปลาคังใส่ตูน |
| Nan | `north_6_2.pdf` | — | ขนมปาดงาม่อน |
| Nan | `north_6_3.pdf` | — | ห่อนึ่งไก่ |
| Surin | `northeast_15_1.pdf` | `transmitted` | ซันลอเจก (แกงกล้วย) |
| Surin | `northeast_15_2.pdf` | `transmitted` | ซันลอตราวมะออม (แกงเผือกใส่อีออม) |
| Surin | `northeast_15_3.pdf` | `transmitted` | ประเฮาะซัจจรูก (ปลาร้าเนื้อหมู) |

Four of six carry a level, and **all four carry the same level.** Figure 5 is specified as
a confusion matrix whose off-diagonal cells are the interesting ones. With one distinct
official value there is no matrix — there is a single row, and it stays a single row
whatever the cooks say. An agreement statistic over four dishes with zero variance on one
axis is not a finding in either direction.

This is a question-design result, not an extraction failure. **The checkbox pipeline
recovered every endangerment value that exists in the fieldwork provinces.**

## Why a bare percentage would have been the misleading number

"68% recovered" invites the reading that the extractor fails on the other 32%. It does
not. A field is missing for four reasons and only one of them is ours:

| Count | Share | Why endangerment is missing |
|---:|---:|---|
| 157 | 68.0% | **recovered** — a §3 box is ticked and matched |
| 34 | 14.7% | §3 present, every box left empty by the submitter |
| 25 | 10.8% | §3 absent from the document — a form variant without the section |
| 12 | 5.2% | no checkbox glyphs at all — image-only scans |
| 3 | 1.3% | §3 in the text with no box bound — **the only bucket that could be our bug** |

The middle three, 71 documents, are unknowns no extractor could turn into data. An
unticked box is not evidence for option one — Rule 2's logic applies to the endangerment
column as much as to province.

The three unbound documents were read individually rather than counted:

- `central_1_1.pdf` — a **false positive of the bucket test**, not a miss. The needle
  `สืบทอดจากรุ่นสู่รุ่น` appears in prose in a later section ("๑. ขาดการสืบทอดจากรุ่นสู่รุ่น
  เพรา…", explaining *why* the dish is at risk), not as a §3 option. There is no §3
  checkbox in this document to find.
- `south_9_2.pdf`, `south_9_3.pdf` — a **genuine miss**, cause identified below.

## The two corrupted documents

`south_9_2.pdf` and `south_9_3.pdf` carry Latin-1 mojibake: Thai combining marks arrive as
accented Latin letters, so `ที` reads as `ทีÉ`. §5 names sara am (ำ) dropping to a space as
a trap that "fails silently and corrupts ingredient names rather than throwing an error",
and this is the same class of defect in a different disguise.

Its cost, measured rather than assumed:

| | mojibake documents (2) | the other 229 |
|---|---|---|
| endangerment recovered | 0 / 2 | 157 / 229 (68.6%) |
| dish_category recovered | 2 / 2 | 172 / 229 (75.1%) |
| mean ingredient rows | **0.0** | 4.9 |

The endangerment loss is visible in the raw text — `south_9_2.pdf` contains
` เป็นเมนูทีÉใกล้จะสูญหายและหารับประทานยาก`, where `U+F0FE` is a *checked* box, so its
true value is `near_lost` and the extractor returns nothing. The label binding truncates at
`'เป็นเมนูที'`, before it reaches the needle.

**The larger cost is the ingredient table, not the checkbox.** Both documents yield zero
ingredient rows against a corpus mean of 4.9. That is two recipes silently absent from the
dataset rather than two fields absent from a record.

**Not fixed here, deliberately.** It cannot change the RQ5 answer — both documents are in
the South, and RQ5's sample is Nan and Surin — so fixing it inside the go/no-go would have
been scope creep into a measurement that had already answered its question. It is logged
as a defect to be scheduled on its own terms.

## What this does not say

- It does not say the four recovered fieldwork values are *correct*. They are what the
  extractor reads from a ticked box; confirming them against the PDFs by eye is a separate
  and much smaller job than confirming 157.
- It does not say RQ5 is dead. It says RQ5 **as specified in §6** has no variance to
  measure. Whether to reframe, widen the fieldwork provinces, or replace the question is
  an HD decision and is recorded as an open gate in `docs/decisions.md`.
- It does not touch `dish_category`, which recovers at 75.3% across the corpus and is
  load-bearing for other questions independently of RQ5.

## Provenance

The corpus was fetched 2026-08-16 under HD-3 (`dcp_food`) **option C** — reference layer
only, excluded from any public release, pending a reply to
`docs/dcp_permission_request.md`. Nothing in this measurement is published, and nothing
here writes to the database.
