"""RQ1 rebuilt at region level: is there any regional signal in ingredient composition?

    uv run python -m scripts.rq1_region_level [--permutations N]

CLAUDE.md §4 specifies RQ1 as a distance-decay curve with change-point detection and a
boundary width in kilometres. At a 1.3% labelled fraction §4's own constraint collapses
the unit to four regions, and four units give six pairwise distances — too few for a fit,
a change point, or a Mantel test that is not already at its p-value floor. See
`src.analyze.region_signal` for that argument in full.

This runs the question underneath it instead: does region membership explain ingredient
composition at all? The unit is the recipe, so n is the number of labelled recipes.

**Three cohorts, because the unit of observation is genuinely uncertain.** A kapook page
may carry one dish or forty-six, and pooling a roundup's ingredients into a single vector
mixes dishes that have nothing to do with each other:

``single``
    Pages with exactly one ingredient section. The cleanest unit and the reported one.
``paired``
    Up to two sections — a dish plus its sauce, mostly.
``pooled``
    Every labelled page, roundups included. Reported to show what pooling does, not
    because it is a better estimate.

Labels come from the researcher-confirmed dish attributions in
`docs/kapook_province_hits_audit.csv` first, and from an unambiguous region term in the
page text otherwise. A page whose evidence points at two regions is left unlabelled —
rule 2's spirit: no nearest-neighbour filling, no "probably Central".

Nothing here writes to the database. Tokenisation is provisional pending HD-6.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from scripts.measure_labelled_fraction import region_hits
from src.analyze.region_signal import (
    group_centroid_distances,
    holm_adjust,
    ingredient_tokens,
    separation_test,
)
from src.config import DATA_DIR, RANDOM_SEED, RAW_DIR
from src.ingest.kapook_page import article_lines, parse_file

CORPUS = RAW_DIR / "kapook_cooking"
AUDIT = Path("docs/kapook_province_hits_audit.csv")
COHORTS = {"single": 1, "paired": 2, "pooled": 10_000}


def confirmed_dish_regions() -> dict[str, str]:
    """page_id -> region4, for the 33 rows the researcher confirmed as dish labels.

    The audit file keys on the filename stem (``view100003``); ``KapookRecord.page_id`` is
    the digits alone. Stripping the prefix here rather than at the call site keeps the
    mismatch in one place — an earlier version joined on the raw key, matched nothing, and
    reported a corpus labelled entirely by region term without erroring.
    """
    with AUDIT.open(encoding="utf-8") as handle:
        regions = {
            row["page_id"].removeprefix("view"): row["region4"]
            for row in csv.DictReader(handle)
            if row["verdict"] == "dish"
        }
    if not regions:
        raise SystemExit(f"no confirmed dish rows in {AUDIT}")
    return regions


def build_corpus() -> list[dict[str, object]]:
    dish_regions = confirmed_dish_regions()
    records = []
    for path in sorted(CORPUS.glob("view*.html")):
        record = parse_file(path)
        if not record.is_usable:
            continue
        tokens = [t for section in record.sections for item in section.items
                  for t in ingredient_tokens(item)]
        if not tokens:
            continue

        by_dish = dish_regions.get(record.page_id)
        by_term = region_hits(
            "\n".join(article_lines(path.read_text(encoding="utf-8", errors="replace")) or [])
        )
        # A confirmed dish attribution outranks a region term in the prose: it was read by
        # a person, and it is about the dish rather than about the article.
        if by_dish:
            region = by_dish
        elif len(by_term) == 1:
            region = next(iter(by_term))
        else:
            region = None

        records.append({
            "page_id": record.page_id,
            "region": region,
            "n_sections": len(record.sections),
            "tokens": tokens,
            "label_source": "confirmed_dish" if by_dish else ("region_term" if region else None),
        })
    return records


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--permutations", type=int, default=9_999)
    args = ap.parse_args()

    records = build_corpus()
    print(f"corpus: {len(records)} pages with tokenisable ingredients")

    # Document frequencies come from the whole corpus, not from the labelled subset. With
    # 58 labelled recipes the IDF of a common ingredient would otherwise be estimated from
    # 58 documents, and a token absent from those 58 by chance would look distinctive.
    vectorizer = TfidfVectorizer(analyzer=lambda tokens: tokens, min_df=2)
    matrix = vectorizer.fit_transform([r["tokens"] for r in records]).toarray()
    print(f"vocabulary: {len(vectorizer.vocabulary_)} tokens (min_df=2), "
          f"fitted on all {len(records)} pages")

    index = {r["page_id"]: i for i, r in enumerate(records)}
    results = {}
    for name, max_sections in COHORTS.items():
        cohort = [r for r in records if r["region"] and r["n_sections"] <= max_sections]
        if len(cohort) < 8:
            print(f"\n{name}: n={len(cohort)} — too few to test")
            continue
        rows = np.array([index[r["page_id"]] for r in cohort])
        labels = [str(r["region"]) for r in cohort]
        result = separation_test(matrix[rows], labels, args.permutations, RANDOM_SEED)
        results[name] = result
        sizes = ", ".join(f"{k}={v}" for k, v in sorted(result.group_sizes.items()))
        print(f"\n{name}: n={result.n_recipes}  ({sizes})")
        print(f"  mean cosine distance  within {result.within:.4f} | "
              f"between {result.between:.4f}")
        print(f"  separation {result.separation:+.4f}   "
              f"p = {result.p_value:.4f} ({result.n_permutations} permutations)")
        print(f"  {'signal' if result.significant else 'NO SIGNAL at alpha=0.05'}")

    strict = [r for r in records if r["region"] and r["n_sections"] <= COHORTS["single"]]
    pairwise: dict[str, dict[str, float]] = {}
    holdout: dict[str, dict[str, float]] = {}
    if strict:
        rows = np.array([index[r["page_id"]] for r in strict])
        labels = [str(r["region"]) for r in strict]
        names, centroids = group_centroid_distances(matrix[rows], labels)
        print("\ncentroid cosine distance, single-section cohort (six numbers, not a curve):")
        print("            " + "".join(f"{n:>12}" for n in names))
        for i, name in enumerate(names):
            print(f"{name:>12}" + "".join(f"{centroids[i][j]:12.4f}" for j in range(len(names))))

        # §4 asks which boundary is sharpest. With six pairs that question is answered by
        # testing each pair, not by finding a change point on a curve.
        print("\npairwise separation, single-section cohort:")
        for i, first in enumerate(names):
            for second in names[i + 1:]:
                pair = [r for r in strict if r["region"] in (first, second)]
                pair_rows = np.array([index[r["page_id"]] for r in pair])
                result = separation_test(
                    matrix[pair_rows], [str(r["region"]) for r in pair],
                    args.permutations, RANDOM_SEED,
                )
                pairwise[f"{first}|{second}"] = {
                    "n": result.n_recipes, "separation": result.separation,
                    "p": result.p_value,
                }
        # Six comparisons on four regions is a family. Reporting six raw p-values invites
        # the reader to pick the smallest one.
        adjusted = holm_adjust({k: v["p"] for k, v in pairwise.items()})
        for key, entry in pairwise.items():
            entry["p_holm"] = adjusted[key]
            first, second = key.split("|")
            flag = "  *" if adjusted[key] < 0.05 else ""
            print(f"  {first:>10} vs {second:<10} n={entry['n']:3}  "
                  f"sep {entry['separation']:+.4f}  p = {entry['p']:.4f}  "
                  f"Holm = {adjusted[key]:.4f}{flag}")

        # Northeast is 28 of 58. If it carries the whole effect, that is a narrower finding
        # than "regions differ" and the difference must not be hidden inside one p-value.
        print("\nleave-one-region-out, single-section cohort:")
        for dropped in names:
            kept = [r for r in strict if r["region"] != dropped]
            if len(set(str(r["region"]) for r in kept)) < 2 or len(kept) < 8:
                continue
            kept_rows = np.array([index[r["page_id"]] for r in kept])
            result = separation_test(
                matrix[kept_rows], [str(r["region"]) for r in kept],
                args.permutations, RANDOM_SEED,
            )
            holdout[dropped] = {"n": result.n_recipes, "separation": result.separation,
                                "p": result.p_value}
            flag = "  *" if result.significant else "   NO SIGNAL"
            print(f"  without {dropped:<10} n={result.n_recipes:3}  "
                  f"sep {result.separation:+.4f}  p = {result.p_value:.4f}{flag}")

    sources = Counter(r["label_source"] for r in records if r["region"])
    print(f"\nlabel provenance: {dict(sources)}")

    out = DATA_DIR / "coverage" / "rq1_region_signal.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "seed": RANDOM_SEED,
        "permutations": args.permutations,
        "vocabulary": len(vectorizer.vocabulary_),
        "cohorts": {k: vars(v) for k, v in results.items()},
        "pairwise_single": pairwise,
        "leave_one_out_single": holdout,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
