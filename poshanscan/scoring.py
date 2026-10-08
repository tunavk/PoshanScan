"""Deterministic nutrient scoring. No AI here on purpose: health claims must be predictable and citable.

"High in" thresholds follow Chile's front-of-pack warning law (final phase, Ley 20.606),
the model the proposal borrows its visual logic from (Taillie et al., 2020).
Daily limits follow ICMR-NIN Dietary Guidelines for Indians (2024):
  added sugar < 25 g/day, salt < 5 g/day, saturated fat < 10% of energy (~22 g on 2000 kcal).
Note: labels report total sugar, so naturally sweet items (lassi, juice) are judged on total sugar.
"""
from dataclasses import dataclass

from .products import Product

THRESHOLDS = {  # per 100 g (solid) / per 100 ml (liquid)
    "solid":  {"sugar": 10.0, "salt": 400.0, "satfat": 4.0},
    "liquid": {"sugar": 5.0,  "salt": 100.0, "satfat": 3.0},
}
DAILY_LIMIT = {"sugar": 25.0, "salt": 5.0, "satfat": 22.0}  # grams per day


@dataclass
class Verdict:
    product: Product
    nutrient: str | None        # worst nutrient, or None if nothing is high
    ratio: float                # how many times over the "high" threshold
    amount_serving: float = 0   # grams of sugar / salt / sat fat in one serving
    pct_daily: float = 0        # % of ICMR-NIN daily limit in one serving

    @property
    def is_high(self) -> bool:
        return self.nutrient is not None


def _per100(p: Product, nutrient: str) -> float | None:
    return {"sugar": p.sugar_g, "salt": p.sodium_mg, "satfat": p.satfat_g}[nutrient]


def score(p: Product) -> Verdict:
    limits = THRESHOLDS[p.form]
    worst, worst_ratio = None, 0.0
    for nutrient, limit in limits.items():
        v = _per100(p, nutrient)
        if v is not None and v / limit > worst_ratio:
            worst, worst_ratio = nutrient, v / limit
    if worst is None or worst_ratio < 1:
        return Verdict(p, None, worst_ratio)

    serving = p.serving or 100
    per100 = _per100(p, worst)
    if worst == "salt":
        amount = per100 / 1000 * 2.5 * serving / 100  # sodium mg -> salt g
    else:
        amount = per100 * serving / 100
    return Verdict(p, worst, worst_ratio, amount, 100 * amount / DAILY_LIMIT[worst])


def amount_of(p: Product, nutrient: str) -> float | None:
    """Per-100 value, used to check that a swap is genuinely better."""
    return _per100(p, nutrient)
