"""Deterministic nutrient scoring. No AI here on purpose: health claims must be predictable and citable.

Rules and numbers come from the team's food database ("Read Me" sheet -> data/team/settings.json):
- "High in" limits follow Chile's front-of-pack warning law (Ley 20.606, final stage), the model the
  proposal borrows its visual logic from (Taillie et al., 2020). Edit them in the spreadsheet the day
  FSSAI notifies its own numbers and re-run scripts/import_team_db.py.
- A warning fires only when a value is strictly greater than its limit.
- Sugar uses added sugar when the label gives it, otherwise total sugar ("total sugar basis").
- Daily limits follow ICMR-NIN Dietary Guidelines for Indians (2024): added sugar 25 g, salt 5 g.
- Grades: each nutrient's ratio to its limit gives A (<= 0.25), B (<= 0.5), C (<= 1, no warning),
  D (<= 2) or E (> 2). The overall grade is the worst letter; "?" when nothing is known.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

from .model import Product

_SETTINGS_FILE = Path(__file__).parent / "data" / "team" / "settings.json"
_DEFAULTS = {
    "limits": {"solid": {"sugar": 10.0, "salt": 400.0, "satfat": 4.0},
               "liquid": {"sugar": 5.0, "salt": 100.0, "satfat": 3.0}},
    "daily": {"sugar_g": 25.0, "salt_g": 5.0},
    "sugar_per_tsp_g": 4.0, "salt_per_sodium": 2.5,
    "grade_bands": {"A": 0.25, "B": 0.5, "C": 1.0, "D": 2.0},
}
SETTINGS = json.loads(_SETTINGS_FILE.read_text()) if _SETTINGS_FILE.exists() else _DEFAULTS

THRESHOLDS = SETTINGS["limits"]  # per 100 g (solid) / per 100 ml (liquid); "salt" limit is sodium in mg
# Saturated fat has no ICMR-NIN gram limit in the team sheet; ~22 g is 10% of a 2000 kcal day.
DAILY_LIMIT = {"sugar": SETTINGS["daily"]["sugar_g"], "salt": SETTINGS["daily"]["salt_g"], "satfat": 22.0}
TSP_G = SETTINGS["sugar_per_tsp_g"]
SALT_PER_SODIUM = SETTINGS["salt_per_sodium"]
GRADE_ORDER = "ABCDE"


@dataclass
class Verdict:
    product: Product
    nutrient: str | None        # worst nutrient over its limit, or None if nothing is high
    ratio: float                # how many times its limit the worst nutrient is
    amount_serving: float = 0   # grams of sugar / salt / sat fat in one serving (worst nutrient)
    pct_daily: float = 0        # % of the daily limit in one serving (worst nutrient)
    highs: list[str] = field(default_factory=list)   # every nutrient over its limit, worst first
    grade: str = "?"            # overall A-E, "?" when no nutrient is known
    grades: dict = field(default_factory=dict)       # per nutrient

    @property
    def is_high(self) -> bool:
        return self.nutrient is not None

    @property
    def no_data(self) -> bool:
        return self.grade == "?"

    @property
    def sugar_basis(self) -> str:
        return "added" if self.product.added_sugar_g is not None else "total"


def amount_of(p: Product, nutrient: str) -> float | None:
    """Per-100 value used for the "high in" check (sugar = added sugar when known)."""
    return {"sugar": p.sugar_used, "salt": p.sodium_mg, "satfat": p.satfat_g}[nutrient]


def _letter(ratio: float) -> str:
    for g, upto in SETTINGS["grade_bands"].items():
        if ratio <= upto:
            return g
    return "E"


def per_serving(p: Product, nutrient: str) -> float | None:
    """Grams of sugar / salt / sat fat in one serving."""
    v = amount_of(p, nutrient)
    if v is None:
        return None
    serving = p.serving or 100
    if nutrient == "salt":
        return v / 1000 * SALT_PER_SODIUM * serving / 100  # sodium mg -> salt g
    return v * serving / 100


def score(p: Product) -> Verdict:
    limits = THRESHOLDS[p.form]
    ratios = {n: amount_of(p, n) / lim for n, lim in limits.items() if amount_of(p, n) is not None}
    grades = {n: _letter(r) for n, r in ratios.items()}
    grade = max(grades.values(), key=GRADE_ORDER.index) if grades else "?"
    highs = sorted((n for n, r in ratios.items() if r > 1), key=lambda n: -ratios[n])
    if not highs:
        return Verdict(p, None, max(ratios.values(), default=0.0), grade=grade, grades=grades)
    worst = highs[0]
    amount = per_serving(p, worst)
    return Verdict(p, worst, ratios[worst], amount, 100 * amount / DAILY_LIMIT[worst],
                   highs=highs, grade=grade, grades=grades)
