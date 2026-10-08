"""Product lookup: curated CSV first, then Open Food Facts as a fallback."""
import csv
import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path

import httpx

DATA = Path(__file__).parent / "data"
OFF_URL = "https://world.openfoodfacts.org/api/v2/product/{}.json"
OFF_HEADERS = {"User-Agent": "PoshanScan/0.1 (student research prototype)"}

# Open Food Facts category tag -> our category. First match wins.
OFF_CATEGORY_MAP = [
    ("instant-noodles", "noodles"), ("noodles", "noodles"),
    ("energy-drinks", "energy_drink"),
    ("sodas", "soft_drink"), ("carbonated", "soft_drink"), ("colas", "soft_drink"),
    ("juices", "juice_drink"), ("fruit-based-beverages", "juice_drink"), ("nectars", "juice_drink"),
    ("chocolates", "chocolate"), ("candies", "chocolate"), ("confectioneries", "chocolate"),
    ("biscuits", "biscuit"), ("cookies", "biscuit"), ("cakes", "biscuit"),
    ("chips", "chips"), ("crisps", "chips"), ("salty-snacks", "chips"), ("popcorn", "chips"),
    ("breakfast-cereals", "cereal"), ("ketchup", "condiment"), ("sauces", "condiment"),
    ("spreads", "spread"), ("dairy-drinks", "dairy_drink"), ("fermented-milk", "dairy_drink"),
    ("beverages", "juice_drink"),
]


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


def _num(v):
    try:
        return float(v) if v not in ("", None) else None
    except ValueError:
        return None


def _load_products() -> list[Product]:
    out = []
    with open(DATA / "products.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            serving = _num(r["serving"]) or _num(r["pack"])
            out.append(Product(
                name=r["name"], category=r["category"], form=r["form"],
                sugar_g=_num(r["sugar_g"]), sodium_mg=_num(r["sodium_mg"]),
                satfat_g=_num(r["satfat_g"]), kcal=_num(r["kcal"]),
                serving=serving, pack=_num(r["pack"]), price_inr=_num(r["price_inr"]),
                barcode=r["barcode"].strip(), source=r["source"],
                aliases=[a.strip().lower() for a in r["aliases"].split("|") if a.strip()],
            ))
    return out


PRODUCTS = _load_products()
BY_BARCODE = {p.barcode: p for p in PRODUCTS if p.barcode}


def by_barcode(code: str) -> Product | None:
    code = re.sub(r"\D", "", code)
    if not code:
        return None
    if code in BY_BARCODE:
        return BY_BARCODE[code]
    return _open_food_facts(code)


def _open_food_facts(code: str) -> Product | None:
    try:
        r = httpx.get(OFF_URL.format(code), headers=OFF_HEADERS, timeout=8,
                      params={"fields": "product_name,brands,categories_tags,nutriments,serving_quantity"})
        data = r.json()
    except (httpx.HTTPError, ValueError):
        return None
    if data.get("status") != 1:
        return None
    p = data["product"]
    n = p.get("nutriments", {})
    sugar, sodium, satfat = n.get("sugars_100g"), n.get("sodium_100g"), n.get("saturated-fat_100g")
    if sugar is None and sodium is None and satfat is None:
        return None
    tags = " ".join(p.get("categories_tags", []))
    category = next((ours for key, ours in OFF_CATEGORY_MAP if key in tags), "any")
    liquid = "beverages" in tags or category.endswith("drink")
    name = " ".join(x for x in [p.get("brands", "").split(",")[0], p.get("product_name", "")] if x).strip()
    return Product(
        name=name or f"Product {code}", category=category,
        form="liquid" if liquid else "solid",
        sugar_g=_num(sugar), satfat_g=_num(satfat), kcal=_num(n.get("energy-kcal_100g")),
        sodium_mg=_num(sodium) * 1000 if _num(sodium) is not None else None,
        serving=_num(p.get("serving_quantity")), barcode=code, source="Open Food Facts",
    )


def by_name(text: str) -> Product | None:
    """Fuzzy-match a shopping-list line like '2 packets maggi' to a product."""
    q = re.sub(r"[^a-z0-9' -]", " ", text.lower())
    q = re.sub(r"\b\d+\s*(x|pcs?|packets?|packs?|bottles?|kg|g|gm|ml|l|ltr)?\b", " ", q)
    q = " ".join(q.split())
    if len(q) < 2:
        return None
    # 1) an alias appears as a whole word/phrase in the line (longest alias wins)
    best, best_len = None, 0
    for p in PRODUCTS:
        for a in p.aliases + [p.name.lower()]:
            if len(a) > best_len and re.search(rf"(?<![a-z]){re.escape(a)}(?![a-z])", q):
                best, best_len = p, len(a)
    if best:
        return best
    # 2) close spelling (e.g. "kurkuray", "bournvitta")
    names = {a: p for p in PRODUCTS for a in p.aliases}
    for word in [q] + q.split():
        hit = difflib.get_close_matches(word, names.keys(), n=1, cutoff=0.8)
        if hit:
            return names[hit[0]]
    return None
