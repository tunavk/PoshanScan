"""The Product record shared by every data source."""
import re
from dataclasses import dataclass, field

# Where a product's numbers came from, most trusted first.
#   curated     - our own products.csv (to be checked against real packs by the team)
#   imported    - Open Food Facts India, passed quality.py checks
#   confirmed   - 2+ shoppers' label photos that agree
#   contributed - 1 shopper's label photo
#   label photo - the label this user just sent (not saved as a product)
TRUST_ORDER = ["curated", "imported", "confirmed", "contributed"]


@dataclass
class Product:
    name: str
    category: str
    form: str                   # "solid" (per 100 g) or "liquid" (per 100 ml)
    sugar_g: float | None       # per 100 g/ml
    sodium_mg: float | None
    satfat_g: float | None
    kcal: float | None
    serving: float | None = None  # g or ml usually eaten in one go
    pack: float | None = None     # g or ml in the pack
    price_inr: float | None = None  # pack MRP
    barcode: str = ""
    source: str = "curated"
    aliases: list[str] = field(default_factory=list)

    @property
    def price_per_serving(self) -> float | None:
        if self.price_inr is None or not self.pack:
            return None
        return self.price_inr * (self.serving or self.pack) / self.pack

    @property
    def unit(self) -> str:
        return "ml" if self.form == "liquid" else "g"


def num(v):
    try:
        return float(v) if v not in ("", None) else None
    except (TypeError, ValueError):
        return None


STOPWORDS = {"the", "and", "with", "of", "new", "pack", "classic", "original", "flavour", "flavor"}


def tokens(text: str) -> set[str]:
    """Lower-case words for name matching ("Lay's Cream & Onion" -> {"lays", "cream", "onion"})."""
    words = re.findall(r"[a-z0-9]+", text.lower().replace("'", ""))
    return {w for w in words if len(w) > 1 and w not in STOPWORDS and not w.isdigit()}


def match_score(query: set[str], candidate: set[str]) -> float:
    """0..1: how well a candidate's name covers what the user (or photo) said.
    Weighted to recall, so a photo reading "Maggi Masala" matches "Maggi 2-Minute Masala Noodles"."""
    if not query or not candidate:
        return 0.0
    def hit(word, pool):
        return any(word == c or (len(word) >= 4 and (c.startswith(word) or word.startswith(c))) for c in pool)
    recall = sum(hit(w, candidate) for w in query) / len(query)
    precision = sum(hit(c, query) for c in candidate) / len(candidate)
    return 0.75 * recall + 0.25 * precision
