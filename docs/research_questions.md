# The five research questions (Bible v4)

**Authority:** `FlavorMap_Project_Bible_v4.md` §6. This file is the repository's one copy of
the questions. Where it and the Bible disagree, the Bible wins, except where a dated
decision in `docs/decisions.md` has changed the Bible and the Bible is not yet amended.
That applies in one place: the fieldwork provinces are **Nakhon Ratchasima and Buri Ram**
(HD-32, 2026-09-29), where the Bible says Nan and Surin (amendment pending, TIMELINE T1.11).

Each question is stated twice: precisely, for the paper, and plainly, for the site,
interviews and the build log. Each also states what a "no" looks like, because a null
result ships (CLAUDE.md §1, rule 9).

**Four of the five need fieldwork and one needs cooking.** A cancelled trip does not weaken
the paper; it removes questions from it.

| RQ | Question | Needs | Figure | Waiting on |
|---|---|---|---|---|
| 1 | Do the state, the market and the kitchen agree on what a province eats? | fieldwork | 1, register triangle | the lexicon (HD-6\*), the commercial register's province labels (HD-Kapook\*, TIMELINE T1.14), interviews |
| 2 | Is regional identity built from what's included or what's refused? | fieldwork, for validation | 2, distinctiveness decomposition | the measure's definition (HD-13\*), the lexicon, interview Q9 |
| 3 | What does the official record leave out? | fieldwork, entirely | 3, official-record overlap | interviews |
| 4 | Can you cook a dish from the normalised dataset? | cooking, entirely | 4, pipeline fidelity | the lexicon, 8 cook-alongs |
| 5 | Do cooks agree with the state about which dishes are disappearing? | fieldwork, entirely | 5, endangerment agreement | interviews; the six checkbox readings verified by eye (T0.4) |

\* A proposed gate with no entry in `docs/decisions.md` yet. The numbers come from CLAUDE.md §9's
unconfirmed list; HD-Kapook is TIMELINE's name.

---

## RQ1: Do the state, the market and the kitchen agree on what a province eats?

*Plain: does the food the government picks to represent your province match what people
there actually cook?*

- **Method.** The ingredient-profile distance between the three registers for the same
  province: cosine distance on normalised ingredient vectors, pairwise (official↔commercial,
  official↔domestic, commercial↔domestic).
- **Output.** A triangle per province, one vertex per register, with edge length as the
  disagreement (Figure 1).
- **A no looks like.** The three registers agree, so official selection and web recipes
  faithfully represent domestic practice.
- **Transferable claim.** Cultural corpora carry the selection pressure of whoever
  assembled them.

The spine of the paper. The domestic vertex exists only for the two fieldwork provinces;
every other province is a two-register line.

## RQ2: Is regional identity built from what's included or what's refused?

*Plain: is a region's food about what it uses, or about what it refuses to use?*

- **Method.** Decompose each province's distinctiveness into presence-driven and
  absence-driven parts, and validate the result against the absences cooks state in
  interview Q9.
- **Output.** A scatter of presence-driven against absence-driven, one point per province,
  with the diagonal marking balance (Figure 2).
- **A no looks like.** Distinctiveness is symmetric everywhere.
- **Transferable claim.** Every standard distinctiveness measure (TF-IDF, log-odds, Zeta)
  measures presence only. Absence is invisible to all of them.

No off-the-shelf measure exists, so it has to be defined and defended (proposed gate HD-13). Question 9
is asked out loud exactly as written:

> **อะไรที่คนจังหวัดอื่นใส่ในจานนี้ แต่บ้านเราไม่มีวันใส่?**
> *What do people in other provinces put in this that we would never put in?*

## RQ3: What does the official record leave out?

*Plain: whose cooking didn't make the government's list?*

- **Method.** The state selected 3 dishes per province. Ask cooks in Nakhon Ratchasima and
  Buri Ram what they actually cook, and measure the overlap at dish and ingredient level.
- **Output.** A table of dishes and ingredients that cooks name but no register contains,
  plus stacked bars (Figure 3). The "in neither register" segment is the finding.
- **A no looks like.** High overlap, which validates the state's selection.
- **Transferable claim.** Heritage designation is a sampling procedure with a bias, and the
  bias is measurable.

Framed as an **existence claim**, which n≈6 cooks per province supports, and never as a
basis for ranking provinces.

## RQ4: Can you cook a dish from the normalised dataset?

*Plain: after the computer cleans up a recipe, is it still a recipe?*

- **Method.** Cook 8 dishes from the **cleaned dataset's** ingredient list, not the source
  page. Log what was missing, substituted or destroyed, and whether the result was
  recognisable.
- **Output.** A fidelity matrix: 8 dishes × {quantities, order, technique, specificity,
  completeness}, each cell survived, degraded or lost (Figure 4,
  `figures/fidelity_matrix.png`).
- **A no looks like.** Everything cooks fine, so normalisation is lossless in practice.
- **Transferable claim.** Tokenisation and canonicalisation silently delete information,
  and nobody measures how much.

Logged through `cook_along_log` (`make cook-along`). At least two of the eight dishes are
ones the classifier gets wrong (CLAUDE.md §7.4).

## RQ5: Do cooks agree with the state about which dishes are disappearing?

*Plain: the government says these dishes are at risk. Do the people who cook them agree?*

- **Method.** Compare the endangerment level in the government forms with what cooks in
  Nakhon Ratchasima and Buri Ram say about the same dishes.
- **Output.** An agreement matrix, official level against the level cooks report
  (Figure 5). The off-diagonal cells are the interesting ones.
- **A no looks like.** Full agreement, which validates the state's assessment.
- **Transferable claim.** Official risk assessments of cultural practice can be checked
  against practitioners, and the disagreements are informative.

The RQ5 gate was decided on 2026-09-29: option B, through HD-29 and HD-32 (`docs/decisions.md`,
"Evidence for RQ5"). On the extractor's readings the
fieldwork sample has two official values, `transmitted` and `near_lost`, both from Buri
Ram. Those readings are not yet verified by eye (T0.4, `scripts/verify_checkboxes.py`).

---

## Retired questions

v3's five questions are retired by Bible v4 §1 and §14.5. The code and figures built for
them are kept in `src/analyze/v3/` and `figures/v3/`, and whether they appear in the paper
is an open researcher decision (CLAUDE.md §6). Superseded plans are in `docs/archive/`.
