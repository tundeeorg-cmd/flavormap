# HD-1 dialect-group rationale — rebuilt, not recovered

**Written:** 2026-09-12. **This is not the "session report" `docs/decisions.md`'s HD-1
entry refers to.** That file does not exist anywhere in this repository's git history —
confirmed by a full-text search across every commit on every branch, including the
initial scaffolding commit that first introduced `decisions.md` already referencing it.
Whatever reasoning originally produced the twelve-province Transitional list and the
three flagged pairs was not captured as an artifact. This document is a **fresh
proposal**, built from general Thai dialectology rather than reconstructed from
whatever was actually said in that earlier session — it may reach different
conclusions than the original did, and should be read as new evidence for HD-1, not
as the missing report recovered.

**A real limitation, stated up front.** This session has no live network access, so
nothing below was checked against a source just now — it is drawn from general
knowledge of Thai dialect geography and should be spot-checked against a primary
source before it is cited anywhere final. The single best one to check it against is
Suwilai Premsrirat's ethnolinguistic mapping work at Mahidol University's Institute of
Language and Culture for Rural Development, which is the closest thing Thailand has to
an authoritative province-level dialect atlas. This document does not decide HD-1 —
`docs/decisions.md`'s HD-1 entry still carries that gate, with the Decision field still
open.

---

## The twelve Transitional provinces

**Tak.** A genuine crossroads rather than a single case: Tak's northern districts
(toward Mae Sot, Tha Song Yang) sit adjacent to the Kam Mueang zone and carry its
influence, while the southern part of the province, closer to Sukhothai and Kamphaeng
Phet, reads as Central-adjacent. No single label fits the province as a whole.

**Phetchaburi** and **Ratchaburi.** Grouped together because the same reasoning
applies to both: the western provinces carry a documented ethnic mix — Lao Song
(also called Song Dam, descendants of 19th-century resettlement from Laos), Karen
communities near the Myanmar border, and Mon populations — layered onto a Central
Thai base. A bare "Central" label erases minority-language communities that a
single-label scheme has no way to represent, which is the same problem Kanchanaburi
below has more acutely.

**Chumphon** and **Prachuap Khiri Khan.** The conventional dialect hinge between
Central and Southern Thai. Chumphon specifically is the point cited in Thai dialect
geography where Southern Thai's characteristic tonal pattern starts to appear in
everyday speech, without yet being the "full" Southern Thai of Nakhon Si Thammarat or
Songkhla. Prachuap Khiri Khan, the narrow province immediately north, shares the same
gradient rather than a clean break.

**Uthai Thani** and **Nakhon Sawan.** Nakhon Sawan sits at the confluence of the Ping,
Nan, Yom, and Wang rivers — historically a crossroads between the Central plains and
river routes north toward Kam Mueang territory, not a boundary defined by a single
clean ethnic or linguistic marker so much as by geography making it a transit and
mixing point. Uthai Thani, immediately adjacent, shares the same edge-of-Central
position without a stronger claim to any other single group.

**Phetchabun.** A highland basin ringed by mountains, historically a destination for
Isaan-Lao migration into what is otherwise Central-adjacent territory, plus proximity
to the lower-Northern zone. The result is a province where more than one group's
speakers live side by side rather than one clearly dominating.

**Loei.** Administratively Isaan, but at the edge of the northeastern plateau where it
borders Phitsanulok and Phetchabun rather than the Isaan heartland, and across the
Mekong from Laos's Luang Prabang region rather than the Vientiane-facing stretch most
of the rest of Isaan sits opposite. Some accounts of Lao dialect variation in Thailand
note Loei's speech patterns differently from the "mainstream" Isaan-Lao spoken further
east (Khon Kaen, Udon Thani, Roi Et) for exactly that reason — it's Lao-adjacent by a
different route.

**Nakhon Ratchasima.** The strongest, best-documented case in the whole list.
**Khorat Thai** (ภาษาโคราช) is treated in Thai linguistics as its own named variety —
neither standard Central Thai nor Isaan-Lao, but a documented blend carrying Central
Thai's vocabulary base with Lao and Khmer tonal and lexical influence layered on top.
Linguists differ on whether to classify it as a Central Thai dialect or an Isaan one,
which is precisely the definition of a case a single-label five-way split cannot
resolve. If any one province on this list deserves to anchor the Transitional
category, it's this one.

**Kanchanaburi.** Thailand's most ethnically mixed western province by most accounts:
Mon and Karen communities along the Myanmar border corridor, Lao Song and Thai Yuan
(Northern Thai) settlement pockets, on a Central Thai administrative base. Same
reasoning as Phetchaburi/Ratchaburi above, more pronounced.

**Satun.** The most distinctive case, and distinctive in the *opposite* direction from
what its administrative grouping suggests. Satun is one of the four provinces of the
historically Malay-Muslim deep south, grouped administratively with Pattani, Yala, and
Narathiwat — but unlike those three, its Malay-Muslim population overwhelmingly speaks
**Southern Thai (Pak Tai)** as an everyday language rather than Pattani Malay (Yawi).
This traces to Satun's distinct 19th/early-20th-century administrative history, which
put it under direct Siamese governance earlier and on different terms than the other
three provinces the 1909 Anglo-Siamese treaty carved out. Where the current CSV places
Satun in Transitional, the honest alternative reading is that it doesn't sit *between*
Dambro-Southern and Malay so much as it demonstrates that the administrative
Malay-Muslim grouping and the linguistic Malay-speaking grouping are not the same
provinces at all — worth stating explicitly rather than folding into a generic
"ambiguous" bucket, since the ambiguity here is conceptual, not gradient.

---

## The three additional flagged pairs

These are not in the Transitional list — they were kept inside a single majority
group despite genuine internal variation, which is exactly why they were flagged for
extra scrutiny rather than quietly accepted.

**Surin / Si Sa Ket / Buri Ram — currently filed as Isaan_Lao.** The best-documented
of the three flagged cases, and the one with the most direct stakes for this project:
Surin is a fieldwork province. These three provinces (plus parts of Sisaket) carry
large, well-documented populations speaking **Northern Khmer** (ภาษาเขมรถิ่นไทย) and
**Kuy** (Kuay/Suay — Surin's Ban Ta Klang area is nationally known as a Kuy elephant-
keeping community) alongside Lao. Filing all three simply as "Isaan_Lao," identically
to Udon Thani or Nong Khai where the Lao substrate is comparatively uncontested, erases
a genuine three-language layering. This isn't an abstract concern for this project —
food67's own Khmer-gloss dish names in Surin (`docs/decisions.md`, food67 report) are
already documented evidence of exactly this substrate showing up in the recipe data
itself, and interview Q4 (self-reported boundary markers) is well positioned to surface
it directly from informants rather than leaving it as an unlabelled database column.

**Sukhothai / Phitsanulok — currently filed as Central.** The softer of the three
flagged cases. Sukhothai is historically significant as the source of the earliest
Thai script (the Ramkhamhaeng inscription), which if anything argues for treating it
as close to the root of Central Thai rather than peripheral to it. Set against that,
some accounts of modern spoken dialect in Sukhothai and neighbouring Phitsanulok
describe retained phonological features — particularly in vowel length and tone —
that pattern with the lower-Northern (Kam Mueang-adjacent) zone rather than with
"pure" Central Thai as spoken in Bangkok or the lower Central Plains, a product of
their geographic proximity to Uttaradit and Phrae. This case is real but weaker than
Khorat's — it rests on general dialect-geography reasoning rather than a named,
separately-classified variety the way Khorat Thai is.

**Nakhon Ratchasima — already Transitional, flagged a second time.** This isn't a
contradiction so much as a sign the original flag (whatever it actually said) was
pointing at something adjacent to the Transitional call already made — most plausibly
the same Khorat Thai classification question above, restated as a "make sure this one
gets real scrutiny" flag rather than a separate province needing a separate answer. No
additional case is offered here beyond the one already made for Nakhon Ratchasima in
the Transitional list.

---

## What this changes, and what it doesn't

Nothing in the database changes from this document alone. It's evidence for HD-1's
still-open Decision field, same as the original CSV assignment was. If anything, it
makes the researcher's job slightly harder rather than easier: Satun's case argues the
current Transitional placement may be conceptually wrong rather than just uncertain,
and the Surin/Si Sa Ket/Buri Ram case argues a Northeast Khmer/Kuy value might belong
in the scheme as a seventh category rather than being absorbed into Isaan_Lao at all —
which is a bigger structural question than HD-1 was originally scoped to answer, and
worth putting to the researcher explicitly rather than quietly deciding it here.
