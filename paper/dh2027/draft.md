<!--
PROVENANCE: first full draft written by Claude (claude.ai chat), 6 Nov 2026, from the
researcher's outline (OUTLINE.md v0.2), decisions (docs/decisions.md), numbers
(paper/dh2027/numbers.md) and T1.21 observations (docs/notebook.md). Every number below
must match numbers.md; run `make paper-audit`. The researcher revises before submission.
Section 1's origin story is deliberately left blank: it must come from cooking the dish
(T1.9), not from memory or from a draft.
-->

# The State's Dish, the Web's Recipe, the Home Kitchen: How Far Apart Are Thailand's Records of Regional Food?

Jenissa Vichiansin — International School Bangkok · github.com/tundeeorg-cmd/flavormap

## 1. The kitchen

[ORIGIN STORY — to be written by the author after cooking the dish with the family member (TIMELINE T1.9). First sentence starts with cooking; method enters no earlier than sentence three. Include what contradicted the remembered version. Do not draft this from memory. ~80 words.]

The version cooked at home is not the version the government lists, nor the one a recipe site publishes. Thailand's Department of Cultural Promotion names three dishes for each of the country's 77 provinces; recipe portals publish thousands more; home cooks make what season, cost and habit allow. Which of these is "Thai regional food"? This paper treats the question as empirical: when the same cuisine is recorded by three actors with three different motives, how far apart are the records, and is the difference larger than chance? This short paper reports the first side of that triangle, the state and the web; interviews with home cooks in Nakhon Ratchasima and Buri Ram, scheduled for November–December 2026, will complete it.

## 2. Background and gap

Computational gastronomy represents recipes as sets of ingredients, an approach established by flavour-network studies (Ahn et al. 2011). Critical dataset studies argue that every corpus carries the choices of whoever assembled it (Gebru et al. 2021), and heritage studies describe state curation as an "authorised" discourse (Smith 2006). These literatures rarely meet in food data.

Three gaps follow. First, no study compares state-curated, commercial and domestic records of the same cuisine for the same places. Second, computational food research treats the ingredient list as the recipe, but no study has checked whether such lists still describe a dish that can be cooked. Third, standard distinctiveness measures such as log-odds (Monroe, Colaresi and Quinn 2008) and Zeta (Burrows 2007) register what a corpus contains, so a region's refusals, the ingredients it would never use, are invisible to them. [TBD: 2–3 Thai food-studies sources.]

## 3. Data: three registers

I treat each source as a *register*: a record of the same cuisine produced under a particular selection pressure (Table 1). None is ground truth; the comparison between them is the instrument.

The **official** register is the Department of Cultural Promotion's local-food programme (`food.culture.go.th`, programme year 2568): 231 submission forms, three dishes per province. I loaded 203 recipes from 74 provinces; 144 have between 3 and 25 mapped ingredients and enter the analysis. The **commercial** register is two Thai recipe portals, Kapook (1,360 recipes) and MThai (193); a third portal is excluded pending the publisher's permission. Web recipes rarely say where a dish comes from: only 86 carry a region claim in their title, category, tags or hand-confirmed body text, and 83 of these enter the analysis. The **domestic** register is a planned set of twelve interviews with home cooks in Nakhon Ratchasima and Buri Ram; none had been completed at submission.

Informants' names, addresses and telephone numbers in the official forms are stripped at parse time, before any database write, and a database-wide test enforces this. Only ingredient lists are stored, never recipe prose; every site's terms are audited and dated; interviews use a Thai consent form with a parent present. Two Thai PDF extraction traps, a vowel that silently drops out and checkboxes drawn in a symbol font, are handled with dedicated tests.

**Table 1.** Three registers (counts at submission).

| Register | Source | Recipes analysed | Selection pressure |
|---|---|---|---|
| Official | DCP local-food forms, 2568 | 144 (of 203 loaded; 74 provinces) | Cultural policy, provincial representation |
| Commercial | Kapook, MThai | 83 region-labelled (of 1,553) | Web publishing, readership, ingredient availability |
| Domestic | Interviews, Nakhon Ratchasima and Buri Ram | 0 (12 planned) | Season, cost, habit, what grows nearby |

## 4. Method

Ingredients are normalised to a controlled Thai vocabulary of 492 entries, built from 5,864 logged mapping decisions and covering 81.4% of ingredient mentions in the two registers analysed. Every granularity rule is documented with its reasoning.

Because web recipes so rarely name a province, the unit is the region: Central, North, Northeast and South. For each region and register I build a TF-IDF-weighted ingredient vector and measure the cosine distance between the official and commercial vectors. To ask whether a distance is larger than chance, I pool each region's recipes and reassign the official and commercial labels 9,999 times, report the share of shuffles at least as distant, and adjust across the four regions with Holm's method. My outline had planned a different null, shuffling region labels; I switched after trial runs because the register shuffle tests RQ1 directly, and I report the planned test as secondary. Each distance carries a 95% bias-corrected bootstrap interval (9,999 resamples). Robustness checks repeat the analysis with prevalence weighting and for each site separately; cells with fewer than five web recipes are flagged.

Later stages test whether regional identity lies in what cooks refuse as much as what they use (interview question 9: "อะไรที่คนจังหวัดอื่นใส่ในจานนี้ แต่บ้านเราไม่มีวันใส่?"), which dishes no record lists, whether dishes can be cooked from ingredient lists alone, and whether state-endangered dishes survive online.

## 5. Preliminary results

The state and web records differ beyond chance in all four regions (Holm-adjusted p = 0.0004–0.0198; Table 2). The gap is general rather than regional: under the secondary test, no region's gap is larger than the others' (0 of 4).

**Table 2.** Official↔commercial cosine distance (TF-IDF, pooled sites).

| Region | n official / web | Distance | 95% CI | p (register shuffle, Holm) |
|---|---|---|---|---|
| Northeast | 34 / 35 | 0.430 | 0.286–0.485 | 0.0004 |
| South | 28 / 18 | 0.494 | 0.393–0.483* | 0.0108 |
| Central | 49 / 18 | 0.568 | 0.453–0.592 | 0.0021 |
| North | 33 / 12 | 0.649 | 0.541–0.649* | 0.0198 |

\*Observed distance lies just outside its bias-corrected interval; cosine distances between small resampled groups are biased upward.

Distances range from 0.430 in the Northeast to 0.649 in the North, in the same order under prevalence weighting. I do not read this ranking as regional disagreement: the region with the most web recipes (35) is closest and the one with the fewest (12) farthest, and small samples inflate cosine distance. Central's result rests on a single collection: 13 of its 18 web recipes come from one portal's Chai Nat tag, and without them the difference is no longer significant (p = 0.193, n = 5). Taken site by site, Kapook alone differs from the state record in the Northeast and the South, and MThai alone only in Central. The pooled result therefore needs both sites. Figure 1 shows the underlying ingredient profiles.

*Figure 1 (appendix). Region × ingredient TF-IDF heatmap, the 60 most variable ingredients, both axes ordered by clustering, faceted by register (official n = 49, 33, 34, 28; web n = 18, 12, 35, 18 for Central, North, Northeast and South).*

## 6. Creativity: cooking as a research method

Recipes are creative practice, and pipelines flatten them into lists. Cooking from the normalised data is a way of testing a dataset that only someone who cooks can perform: the cook notices what the list has lost, from quantities and order to technique. Home cooks' substitutions and refusals are creative acts that neither the state's list nor the web records.

## 7. Limitations and next steps

Each province contributes only three official dishes, so intervals are wide; they are reported, not hidden. The commercial register comes from two portals, and its regional labels are scarce. Fieldwork covers two neighbouring Isaan provinces, and endangerment levels are self-reported by submitters. Next, I will complete the interviews (December 2026), release the lexicon and recipe data openly (January 2027), and finish the full paper by March 2027.

## AI-use disclosure

I used Claude Code (Anthropic) to build the data pipeline and to debug Thai text extraction. Claude (Anthropic) also drafted lexicon entries, which I reviewed and confirmed, and wrote a first draft of this paper's text from my outline, decisions and results, which I then revised. [AUTHOR: state exactly what you rewrote.] Every analytical decision, including vocabulary granularity, labelling rules, thresholds and the choice of statistical test, is mine and is documented with its reasoning in `docs/decisions.md`, including which decisions followed an AI recommendation.

## References

Ahn, Y.-Y., Ahnert, S. E., Bagrow, J. P., and Barabási, A.-L. (2011). Flavor network and the principles of food pairing. *Scientific Reports* 1, 196.

Burrows, J. (2007). All the way through: testing for authorship in different frequency strata. *Literary and Linguistic Computing* 22(1), 27–47.

Gebru, T., Morgenstern, J., Vecchione, B., Vaughan, J. W., Wallach, H., Daumé III, H., and Crawford, K. (2021). Datasheets for datasets. *Communications of the ACM* 64(12), 86–92.

Monroe, B. L., Colaresi, M. P., and Quinn, K. M. (2008). Fightin' words: lexical feature selection and evaluation for identifying the content of political conflict. *Political Analysis* 16(4), 372–403.

Smith, L. (2006). *Uses of Heritage*. London: Routledge.

[TBD: 2–3 Thai food-studies sources.]

[TBD: Department of Cultural Promotion source citation.]

[TBD: OpenFlavorTH repository citation.]
