"""Pick ONE realistic, affordable alternative from the curated swap table."""
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


def _load():
    with open(DATA / "swaps.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


SWAPS = _load()


def pick(v: Verdict) -> Swap | None:
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
