# Research notebook

The researcher's weekly paragraphs. What was tried, what broke, what surprised her, what
she changed her mind about.

## What this is for

Three jobs, in order of importance:

1. **Authorship evidence.** A build log written weekly across fifteen months is
   substantially harder to fabricate than a finished repository. Bible §2 — process
   visibility is one of the three signals a reader actually uses.
2. **Source material for the paper.** The Discussion and Limitations sections are much
   easier to write from a contemporaneous record than from memory in month fourteen.
3. **The failure posts.** Two of the six build-log posts are failure posts by design. They
   come from here.

## How to write it

Prose, not bullets. One paragraph a week is enough. Include the parts that did not work,
the wrong turns, and the things that took four hours because of a typo — those are the
entries that make the rest believable.

**Claude Code does not write in this file.** It may append machine-generated summaries
under a clearly-marked heading (the dataset-freeze manifest, for instance, per the freeze
procedure), but the weekly paragraphs are the researcher's voice and the whole value is
that they are hers.

---

## 2026-08

*(first entry to be written by the researcher)*

Machine-generated context for this window, for reference when writing:

- **2026-08-04** — repository scaffolded; first commit.
- **2026-08-09** — source audit tool built and run against six candidate sources; three of
  the Bible's URLs found stale. Local Postgres 15 + PostGIS replaces the hosted database.
- **2026-08-16** — plan reconciled to Bible v3. Working tree inventoried: the "~300
  SorKorPor recipes" referenced in Bible §21 do not exist in the repository or on the
  machine, so the labelled-fraction measurement has no corpus yet.
- **2026-08-23** — kapook corpus parsed (2,702 pages, 2,521 with a readable ingredient
  list) and Bible §21 item 1 measured: **1.3%** carry a province label that is a claim
  about the dish, against a 35% threshold. Region-level claims reach 6.2%. Homographs
  dominate any looser rule — `เลย` is "at all" in 2,384 pages. This is a coverage paper.
  See `docs/labelled_fraction.md`. The measurement preceded pre-registration for RQ3,
  recorded in `docs/decisions.md`.
- **2026-08-23** — the 78-row province audit was reviewed by the researcher, who agreed
  with all 33 `dish` calls. The 1.3% labelled fraction is confirmed rather than proposed.
