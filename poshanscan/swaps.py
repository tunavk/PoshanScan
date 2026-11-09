"""Pick ONE realistic, affordable alternative.

Team database products carry three matched swaps (Same craving, Cheaper, Best for health); the first
is shown and the other two are kept for the MORE reply. Everything else uses the curated swap table.
"""
import csv
from dataclasses import dataclass

from .products import BY_BARCODE, DATA, Product
from .scoring import THRESHOLDS, Verdict, amount_of

MIN_IMPROVEMENT = 0.25  # a product swap must be at least 25% lower in the flagged nutrient


@dataclass
class Swap:
    text: str
    cost_note: str
    product: Product | None = None
    pct_less: int | None = None
    # Team swaps only:
    label: str = ""                 # Same craving / Cheaper / Best for health
    reason: str = ""                # "Still sweet and crunchy, with no added sugar and plenty of fibre."
    grade: str = ""
    sugar_saved_tsp: float | None = None
    salt_saved_g: float | None = None
    in_moderation: bool = False


def team_swap(s: dict) -> Swap:
    pps = s["price_per_serving"]
    return Swap(
        text=s["name"], cost_note=f"₹{pps:.0f} a serving" if pps is not None else "",
        label=s["label"], reason=s["reason"], grade=s["grade"],
        sugar_saved_tsp=s["sugar_saved_tsp"], salt_saved_g=s["salt_saved_g"],
        in_moderation=s["use_note"] == "in moderation",
    )


def more(p: Product) -> list[Swap]:
    """The team's other swap cards for MORE (Cheaper, Best for health)."""
    return [team_swap(s) for s in p.swaps[1:]]


def _load():
    with open(DATA / "swaps.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


SWAPS = _load()


def pick(v: Verdict) -> Swap | None:
    if v.product.swaps:
        return team_swap(v.product.swaps[0])
    cat, nut = v.product.category, v.nutrient
    for want_cat, want_nut in [(cat, nut), (cat, "any"), ("any", "any")]:
        for row in SWAPS:
            if row["category"] != want_cat or row["nutrient"] != want_nut:
                continue
            s = _build(row, v)
            if s:
                return s
    return None


def _build(row, v: Verdict) -> Swap | None:
    ref = row["swap"]
    if ref.startswith("text:"):
        return Swap(ref[5:], row["cost_note"])
    alt = BY_BARCODE.get(ref)
    if not alt or alt.barcode == v.product.barcode:
        return None
    mine, theirs = amount_of(v.product, v.nutrient), amount_of(alt, v.nutrient)
    if mine is None or theirs is None or mine <= 0:
        return None
    if _new_problems(v.product, alt):
        return None
    improvement = 1 - theirs / mine
    if improvement < MIN_IMPROVEMENT:
        return None
    cost_note = _cost_note(v.product, alt)
    if cost_note is None:  # costs more per serving: a lecture, not a nudge
        return None
    return Swap(alt.name, cost_note or row["cost_note"], alt, round(improvement * 100))


def _cost_note(original: Product, alt: Product) -> str | None:
    """Compare price per serving. None = swap costs more; "" = prices not known yet."""
    mine, theirs = original.price_per_serving, alt.price_per_serving
    if mine is None or theirs is None:
        return ""
    if theirs > mine + 0.5:
        return None
    if mine - theirs >= 1:
        return f"₹{mine - theirs:.0f} cheaper per serving"
    return "about the same price"


def _new_problems(original: Product, alt: Product) -> bool:
    """True if the swap is high in something the original wasn't (e.g. cola -> salty chaas)."""
    for nutrient in ("sugar", "salt", "satfat"):
        a, o = amount_of(alt, nutrient), amount_of(original, nutrient)
        alt_high = a is not None and a >= THRESHOLDS[alt.form][nutrient]
        orig_high = o is not None and o >= THRESHOLDS[original.form][nutrient]
        if alt_high and not orig_high:
            return True
    return False
