"""Is there any regional signal in ingredient composition? — RQ1, rebuilt at region level.

RQ1 as specified in CLAUDE.md §4 is a distance-decay curve with change-point detection:
cosine distance on province TF-IDF against great-circle kilometres, and a boundary width
in kilometres as the output. **That analysis cannot be run on this corpus.** The labelled
fraction is 1.3%, §4's own constraint collapses the unit to four regions, and four units
give six pairwise distances. Six points do not support a LOESS fit or a change point, and
a Mantel test on a 4×4 matrix has only 4! = 24 distinct permutations, so its smallest
achievable p-value is 1/24 ≈ 0.042 — the test is at its floor before any data is seen.

What is testable is the question underneath it: **is region membership associated with
ingredient composition at all?** That test runs at the recipe level, not the region level,
so n is the number of labelled recipes rather than four. It answers a weaker question than
§4 asks — whether there is signal, not where the boundary is or how wide — and it is
reported as that weaker question rather than dressed up as the original.

**Tokenisation is provisional and this is not a published result.** `canonical_ingredients`
is empty and stays empty until HD-6, the gate §9 calls the most important in the project.
Ingredient strings here are segmented with PyThaiNLP `newmm` and filtered against a
stoplist of units and preparation verbs. Nothing in this module writes to the lexicon
tables, and no token here is a canonical id. TF-IDF weighting limits how much the stoplist
can matter — a token common to every recipe is down-weighted whether or not it was listed.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

import numpy as np
from pythainlp.tokenize import word_tokenize

from src.config import RANDOM_SEED

# Measures, not ingredients. Both spellings of each abbreviation appear in the corpus.
UNITS = frozenset("""
กรัม กก กิโลกรัม ขีด ช้อนโต๊ะ ช้อนชา ช้อน ถ้วย ตวง ลูก ใบ หัว แว่น ต้น ฟอง ตัว มล ลิตร
ซีซี กำ ช่อ ฝัก กลีบ ก้อน แผ่น ชิ้น ขวด ห่อ ถุง กระป๋อง ปอนด์ ออนซ์ ทัพพี นิ้ว เม็ด ชุด
แง่ง หยด กระปุก กล่อง ขีดครึ่ง ซอง
""".split())

# Preparation, not composition. §7.2 names หั่น สับ บด ซอย explicitly; the rest were read
# off the corpus.
PREPARATIONS = frozenset("""
หั่น สับ บด ซอย โขลก ทุบ ลวก ต้ม ปิ้ง ย่าง ทอด แกะ ล้าง ผ่า นึ่ง คั่ว ตำ ป่น ฉีก บุบ เจียว
ผัด ปอก ขูด สไลซ์ เต๋า แช่ หมัก ตี ร่อน กรอง คน เคี่ยว ละลาย พัก เด็ด โรย ฝาน สะเด็ด
""".split())

# Function words and quantity hedges. ตามชอบ is rule 3's canonical example of a quantity
# that must never be imputed; here it is simply not a token.
FUNCTION = frozenset("""
สำหรับ พอ พอให้ ตามชอบ ตาม ชอบ เล็กน้อย ประมาณ หรือ และ ที่ ของ ใช้ ไว้ ให้ ท่วม อย่าง
นิด หน่อย ครับ ค่ะ คะ นะ เตรียม ส่วนผสม กับ ใน จาก เป็น มี ไม่ ก็ แล้ว ๆ ได้ ต่อ ด้วย
เพิ่ม ตกแต่ง เสิร์ฟ ราด ครึ่ง ทั้ง อีก ส่วน ท่าน คน
""".split())

STOPWORDS = UNITS | PREPARATIONS | FUNCTION

_PARENTHETICAL = re.compile(r"\([^)]*\)|\*+")
_NUMERIC = re.compile(r"[0-9๐-๙]+(?:[./+\-][0-9๐-๙]+)*")
_NON_THAI_WORD = re.compile(r"^[^ก-๙a-zA-Z]+$")
MIN_TOKEN_CHARS = 2


def ingredient_tokens(line: str) -> list[str]:
    """Content tokens from one raw ingredient line. Provisional — see the module docstring.

    Parentheticals go first: they hold brand notes and substitution advice, not the
    ingredient. Numerals go next, so that `1+1/2` does not survive as three tokens.
    """
    text = unicodedata.normalize("NFC", line)
    text = _NUMERIC.sub(" ", _PARENTHETICAL.sub(" ", text))
    tokens = []
    for token in word_tokenize(text, engine="newmm"):
        token = token.strip()
        if (
            len(token) < MIN_TOKEN_CHARS
            or token in STOPWORDS
            or _NON_THAI_WORD.match(token)
        ):
            continue
        tokens.append(token)
    return tokens


@dataclass
class SeparationResult:
    """Whether labelled groups sit further from each other than from themselves."""

    n_recipes: int
    n_groups: int
    within: float
    between: float
    separation: float          # between - within; > 0 means the labels carry signal
    p_value: float
    n_permutations: int
    group_sizes: dict[str, int]
    #: every permuted separation, in permutation order. Figure 2's second panel draws
    #: these: a non-significant pair has to read as "the observed value sits inside its
    #: null", which needs the null itself and not just a p-value.
    null: list[float] = field(default_factory=list)

    def null_interval(self, lower: float = 2.5, upper: float = 97.5) -> tuple[float, float]:
        percentiles = np.percentile(self.null, [lower, upper])
        return float(percentiles[0]), float(percentiles[1])

    @property
    def significant(self) -> bool:
        return self.p_value < 0.05


def cosine_distances(matrix: np.ndarray) -> np.ndarray:
    """Pairwise cosine distance on the rows of a TF-IDF matrix."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    unit = matrix / norms
    return np.clip(1.0 - unit @ unit.T, 0.0, 2.0)


def _mean_within_between(distances: np.ndarray, codes: np.ndarray) -> tuple[float, float]:
    same = codes[:, None] == codes[None, :]
    upper = np.triu(np.ones_like(distances, dtype=bool), k=1)
    within = distances[upper & same]
    between = distances[upper & ~same]
    return float(within.mean()), float(between.mean())


def separation_test(
    matrix: np.ndarray,
    labels: list[str],
    n_permutations: int = 9_999,
    seed: int = RANDOM_SEED,
) -> SeparationResult:
    """Permutation test: are between-group distances larger than within-group ones?

    The unit is the recipe, so the permutation shuffles recipe labels — which is what
    gives this test power that a 4×4 Mantel cannot have. §5's rule that distance-matrix
    entries are not independent still applies, which is why significance comes from
    permutation and never from a parametric p-value.

    One-sided by construction: the alternative is that regions differ, and a *negative*
    separation would not be evidence for RQ1 in the other direction — it would be noise.
    """
    distances = cosine_distances(matrix)
    codes = np.array(labels)
    within, between = _mean_within_between(distances, codes)
    observed = between - within

    rng = np.random.default_rng(seed)
    shuffled = codes.copy()
    null: list[float] = []
    at_least_as_extreme = 0
    for _ in range(n_permutations):
        rng.shuffle(shuffled)
        null_within, null_between = _mean_within_between(distances, shuffled)
        permuted = null_between - null_within
        null.append(permuted)
        if permuted >= observed:
            at_least_as_extreme += 1

    # +1 in both terms: the observed arrangement is itself one of the possible ones, and
    # omitting it can report p = 0, which no permutation test can support.
    p_value = (at_least_as_extreme + 1) / (n_permutations + 1)
    sizes: dict[str, int] = {}
    for label in labels:
        sizes[label] = sizes.get(label, 0) + 1
    return SeparationResult(
        n_recipes=len(labels),
        n_groups=len(sizes),
        within=within,
        between=between,
        separation=observed,
        p_value=p_value,
        n_permutations=n_permutations,
        group_sizes=sizes,
        null=null,
    )


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values for a family of tests.

    Six pairwise tests on four regions is a family, and reporting six raw p-values invites
    the reader to pick the smallest. Holm rather than Bonferroni because it is uniformly
    more powerful at the same familywise error rate, which matters when three of the six
    comparisons have n under 25 and little power to spare.

    Adjusted values are capped at 1.0 and made monotone in the sort order, so a later
    test never reports a smaller adjusted p than an earlier one.
    """
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    total = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (key, raw) in enumerate(ordered):
        running = max(running, min(1.0, (total - rank) * raw))
        adjusted[key] = running
    return adjusted


def group_centroid_distances(
    matrix: np.ndarray, labels: list[str]
) -> tuple[list[str], np.ndarray]:
    """Cosine distance between group centroids. Four regions give six numbers.

    Reported as a matrix and never as a decay curve: six points cannot carry a fit.
    """
    names = sorted(set(labels))
    codes = np.array(labels)
    centroids = np.vstack([matrix[codes == name].mean(axis=0) for name in names])
    return names, cosine_distances(centroids)
