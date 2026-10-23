"""Product lookup across every source, most trusted first:
curated CSV -> imported Open Food Facts catalogue -> shoppers' contributions -> live Open Food Facts API.
"""
import csv
import difflib
import re
from pathlib import Path

import httpx

from . import catalog, contrib, quality
from .model import TRUST_ORDER, Product, match_score, num, tokens

DATA = Path(__file__).parent / "data"
OFF_URL = "https://world.openfoodfacts.org/api/v2/product/{}.json"
OFF_HEADERS = {"User-Agent": "PoshanScan/0.1 (student research prototype)"}

# Open Food Facts category tag -> our category. Most specific first; first match wins.
# A key matches a tag exactly or as a whole hyphenated part ("potato-crisps" matches "crisps").
OFF_CATEGORY_MAP = [
    ("instant-noodles", "noodles"), ("noodles", "noodles"), ("pastas", "noodles"), ("vermicelli", "noodles"),
    ("energy-drinks", "energy_drink"),
    ("sodas", "soft_drink"), ("carbonated-drinks", "soft_drink"), ("colas", "soft_drink"),
    ("plant-based-milks", "dairy_drink"),
    ("dairy-drinks", "dairy_drink"), ("fermented-milk-drinks", "dairy_drink"), ("milkshakes", "dairy_drink"),
    ("buttermilks", "dairy_drink"), ("lassi", "dairy_drink"),
    ("malted-drinks", "malt_drink"), ("cocoa-and-chocolate-powders", "malt_drink"), ("cocoa-powders", "malt_drink"),
    ("juices", "juice_drink"), ("fruit-juices", "juice_drink"), ("nectars", "juice_drink"),
    ("fruit-based-beverages", "juice_drink"), ("sweetened-beverages", "juice_drink"),
    ("chocolates", "chocolate"), ("candies", "chocolate"), ("confectioneries", "chocolate"),
    ("ice-creams", "chocolate"), ("frozen-desserts", "chocolate"), ("dairy-desserts", "chocolate"),
    ("indian-sweets", "chocolate"), ("desserts", "chocolate"),
    ("biscuits", "biscuit"), ("cookies", "biscuit"), ("cakes", "biscuit"), ("wafers", "biscuit"), ("rusks", "biscuit"),
    ("chips", "chips"), ("crisps", "chips"), ("salty-snacks", "chips"), ("popcorn", "chips"),
    ("namkeen", "chips"), ("bhujia", "chips"), ("extruded-snacks", "chips"), ("fried-snacks", "chips"),
    ("indian-snacks", "chips"),
    ("breakfast-cereals", "cereal"), ("mueslis", "cereal"), ("cereal-flakes", "cereal"),
    ("ketchup", "condiment"), ("sauces", "condiment"), ("pickles", "condiment"), ("condiments", "condiment"),
    ("spreads", "spread"), ("butters", "fat"), ("ghee", "fat"), ("breads", "bread"),
    ("nuts", "healthy_snack"), ("dried-fruits", "healthy_snack"), ("seeds", "healthy_snack"),
    ("fox-nuts", "healthy_snack"), ("roasted-chickpeas", "healthy_snack"),
    ("beverages", "juice_drink"),
]
# Catch-all tags that would otherwise match a key above (nuts and flour are "plant-based-foods-and-beverages").
IGNORED_TAGS = {"plant-based-foods-and-beverages", "beverages-and-beverages-preparations", "beverage-preparations"}
DRINKS = {"soft_drink", "energy_drink", "juice_drink", "dairy_drink"}


def _tag_names(tags) -> list[str]:
    out = []
    for tag in tags or []:
        name = tag.split(":", 1)[-1].lower().replace(" ", "-")
        if name not in IGNORED_TAGS:
            out.append(name)
    return out


def category_from_tags(tags) -> str:
    names = _tag_names(tags)
    for key, ours in OFF_CATEGORY_MAP:
        for n in names:
            if n == key or n.endswith("-" + key) or n.startswith(key + "-"):
                return ours
    return "any"


def is_liquid(tags, unit: str, category: str) -> bool:
    """Liquids are judged per 100 ml with stricter limits, so be sure: sold in ml/litres,
    or a drink category that isn't a powder or concentrate to be mixed."""
    if (unit or "").lower() in ("ml", "l", "cl", "ltr"):
        return True
    if (unit or "").lower() in ("g", "kg", "gm"):
        return False
    names = " ".join(_tag_names(tags))
    return category in DRINKS and not any(w in names for w in ("powder", "preparation", "concentrate", "mix"))


def _load_curated() -> list[Product]:
    out = []
    with open(DATA / "products.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append(Product(
                name=r["name"], category=r["category"], form=r["form"],
                sugar_g=num(r["sugar_g"]), sodium_mg=num(r["sodium_mg"]),
                satfat_g=num(r["satfat_g"]), kcal=num(r["kcal"]),
                serving=num(r["serving"]) or num(r["pack"]), pack=num(r["pack"]),
                price_inr=num(r["price_inr"]), barcode=r["barcode"].strip(), source="curated",
                aliases=[a.strip().lower() for a in r["aliases"].split("|") if a.strip()],
            ))
    return out


PRODUCTS = _load_curated()
BY_BARCODE = {p.barcode: p for p in PRODUCTS if p.barcode}


# ---------- by barcode ----------

def by_barcode(code: str) -> Product | None:
    code = re.sub(r"\D", "", code)
    if not code:
        return None
    return (BY_BARCODE.get(code) or catalog.by_barcode(code) or contrib.by_barcode(code)
            or _open_food_facts(code))


def _open_food_facts(code: str) -> Product | None:
    """Live lookup for products newer than our import. Same quality checks as the import."""
    try:
        r = httpx.get(OFF_URL.format(code), headers=OFF_HEADERS, timeout=8,
                      params={"fields": "product_name,brands,categories_tags,nutriments,serving_quantity,"
                                         "product_quantity,product_quantity_unit"})
        data = r.json()
    except (httpx.HTTPError, ValueError):
        return None
    if data.get("status") != 1:
        return None
    p = data["product"]
    n = p.get("nutriments", {})
    sugar, satfat = num(n.get("sugars_100g")), num(n.get("saturated-fat_100g"))
    sodium = num(n.get("sodium_100g"))
    sodium = sodium * 1000 if sodium is not None else None
    kcal = num(n.get("energy-kcal_100g"))
    if quality.problems(sugar, sodium, satfat, kcal, num(n.get("fat_100g")),
                        num(n.get("carbohydrates_100g")), num(n.get("proteins_100g"))):
        return None
    tags = p.get("categories_tags", [])
    category = category_from_tags(tags)
    liquid = is_liquid(tags, p.get("product_quantity_unit", ""), category)
    product_name = re.sub(r"\b\d{8,14}\b", "", p.get("product_name", "")).strip(" -,")  # some names include the barcode
    name = " ".join(x for x in [p.get("brands", "").split(",")[0], product_name] if x).strip()
    return Product(
        name=name or f"Product {code}", category=category, form="liquid" if liquid else "solid",
        sugar_g=sugar, sodium_mg=sodium, satfat_g=satfat, kcal=kcal,
        serving=num(p.get("serving_quantity")), pack=num(p.get("product_quantity")),
        barcode=code, source="imported",
    )


# ---------- by name ----------

def _clean(text: str) -> str:
    q = re.sub(r"[^a-z0-9' -]", " ", text.lower())
    q = re.sub(r"\b\d+\s*(x|pcs?|packets?|packs?|bottles?|kg|g|gm|ml|l|ltr)?\b", " ", q)
    return " ".join(q.split())


def by_name(text: str) -> Product | None:
    """Typed shopping-list line like '2 packets maggi' -> one product, or None.
    Curated aliases first (people type "maggi", not "Maggi 2-Minute Masala Noodles");
    then the wider catalogue, but only on a strong match so "bread" doesn't hit a random product."""
    q = _clean(text)
    if len(q) < 2:
        return None
    words = tokens(q)
    best, best_len = None, 0
    for p in PRODUCTS:
        for a in p.aliases + [p.name.lower()]:
            if len(a) > best_len and re.search(rf"(?<![a-z]){re.escape(a)}(?![a-z])", q):
                best, best_len = p, len(a)
    if best and words <= tokens(" ".join([best.name] + best.aliases)):
        return best  # the alias explains the whole line ("2 packets maggi")
    # A wider catalogue match only counts if it's strong; one-word lines need a near-exact name.
    hits = search(q, limit=1)
    needed = 0.95 if len(words) == 1 else 0.85
    if hits and hits[0][1] >= needed:
        if not best or hits[0][1] > match_score(words, tokens(" ".join([best.name] + best.aliases))):
            return hits[0][0]  # "haldiram moong dal" is Moong Dal, not our "haldiram" Aloo Bhujia
    if best:
        return best
    names = {a: p for p in PRODUCTS for a in p.aliases}
    for word in [q] + q.split():
        hit = difflib.get_close_matches(word, names.keys(), n=1, cutoff=0.8)
        if hit:
            return names[hit[0]]
    return None


def search(text: str, limit: int = 3) -> list[tuple[Product, float]]:
    """Ranked candidates (product, 0..1 score) from all sources; used for front-of-pack photos."""
    q = tokens(text)
    if not q:
        return []
    found: dict[str, tuple[Product, float]] = {}
    curated = [(p, max(match_score(q, tokens(n)) for n in [p.name] + p.aliases)) for p in PRODUCTS]
    for p, s in curated + catalog.search(text, limit=10) + contrib.search(text, limit=5):
        k = p.barcode or p.name
        if s > 0 and (k not in found or s > found[k][1]):
            found[k] = (p, s)
    rank = {src: i for i, src in enumerate(TRUST_ORDER)}
    ranked = sorted(found.values(), key=lambda x: (-round(x[1], 2), rank.get(x[0].source, 9)))
    # The catalogue has several entries per product (pack sizes, spellings). Two candidates with the
    # same name, or the same category and matching nutrition, are the same product for our purposes:
    # "Which one is it? 1 Frooti 2 Frooti" helps nobody. The best, most trusted one is kept.
    out, seen = [], set()
    for p, s in ranked:
        key = " ".join(sorted(tokens(p.name)))
        if key in seen or any(o.category == p.category and quality.agree(o.__dict__, p.__dict__) for o, _ in out):
            continue
        seen.add(key)
        out.append((p, s))
    return out[:limit]
