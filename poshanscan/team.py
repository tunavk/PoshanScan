"""The team's food database (data/team, built by scripts/import_team_db.py from the spreadsheet).

The most trusted source: 403 products (packaged, QSR chains, street food), each graded and given up to
three matched swaps, plus the 375 healthy alternatives those swaps come from (also scannable/searchable).
"""
import csv
import json
import re
from pathlib import Path

from .model import Product, match_score, num, tokens

TEAM_DIR = Path(__file__).parent / "data" / "team"

# The team's categories / cravings -> the bot's swap categories (used only when a product has no team swaps).
CATEGORY = {
    "biscuit": "biscuit", "bakery": "biscuit", "bread_bakery": "bread", "snack": "chips", "namkeen": "chips",
    "noodles": "noodles", "soup": "noodles", "instant_mix": "noodles", "cereal": "cereal",
    "confectionery": "chocolate", "ice_cream": "chocolate", "drink_powder": "malt_drink", "dairy": "dairy_drink",
}
CRAVING = {"fizzy drink": "soft_drink", "sweet drink": "juice_drink", "milky drink": "dairy_drink",
           "salty crunchy": "chips", "sweet crunchy": "biscuit", "dessert": "chocolate", "spread": "spread"}


def _category(team_category: str, craving: str) -> str:
    return CATEGORY.get(team_category) or CRAVING.get(craving) or "any"


def _rows(name: str) -> list[dict]:
    path = TEAM_DIR / name
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _alternative(r: dict) -> Product:
    return Product(
        name=r["alt_label"] or r["alt_name"], category=CRAVING.get(r["craving"], "any"),
        form="liquid" if r["unit"] == "ml" else "solid",
        sugar_g=num(r["total_sugar_g"]), added_sugar_g=num(r["added_sugar_g"]),
        sodium_mg=num(r["sodium_mg"]), satfat_g=num(r["sat_fat_g"]), kcal=num(r["energy_kcal"]),
        serving=num(r["serving_size"]), pack=num(r["pack_size"]), price_inr=num(r["pack_price_inr"]),
        barcode=r["barcode"], source="team", team_id=r["ID"], confidence=r["confidence"],
        craving=r["craving"], aliases=[r["alt_name"].lower()],
    )


def _swaps(r: dict, alts: dict[str, dict]) -> list[dict]:
    out = []
    for i in (1, 2, 3):
        alt_id = r[f"s{i}_alt_id"]
        if not alt_id:
            continue
        alt = alts.get(alt_id, {})
        out.append({
            "label": r[f"s{i}_label"], "alt_id": alt_id,
            "name": alt.get("alt_label") or r[f"s{i}_alt_name"],
            "serving": r[f"s{i}_serving"], "price_per_serving": num(r[f"s{i}_price_per_serving"]),
            "price_diff": r[f"s{i}_price_diff"], "grade": r[f"s{i}_grade"],
            "sugar_saved_tsp": num(r[f"s{i}_sugar_saved_tsp"]), "salt_saved_g": num(r[f"s{i}_salt_saved_g"]),
            "reason": r[f"s{i}_reason"], "use_note": alt.get("use_note", ""),
        })
    return out


# Variant text that is a research note, not something a shopper should read.
_NOTE_WORDS = ("slum", "village", "not stated", "not named", "unnamed", "presumed", "probable", "likely",
               "lab", "pack)", "single)")


def _clean_variant(variant: str) -> str:
    if any(w in variant.lower() for w in ("slum", "village", "not stated")):
        return ""
    variant = re.sub(r"\s*\(([^)]*)\)", lambda m: "" if any(w in m.group(0).lower() for w in _NOTE_WORDS)
                     else m.group(0), variant)
    return variant.strip(" ,")


def shopper_name(r: dict) -> str:
    """"Kurkure 78 g", "Samosa", "Boost Chocolate 500 g" -- not the sheet's display_name with research notes
    ("Kurkure flavour not stated 78 g", "Street / home Samosa Delhi urban slum (Chanderpuri) 46.66 g")."""
    brand = re.sub(r"\s*\(.*?\)", "", r["brand"]).strip()
    street = brand.lower().startswith("street")
    name = r["product_name"].strip()
    in_name = tokens(name)
    brand_words = " ".join(w for w in brand.split() if not tokens(w) <= in_name)  # "Sunfeast Yippee" + "Yippee Noodles"
    variant = _clean_variant(r["variant"])
    if tokens(variant) <= in_name:  # "Magic Masala" + "Magic Masala"
        variant = ""
    parts = [] if street else [brand_words]
    parts += [name, variant]
    size = num(r["pack_size"])
    if size and not street and r["category"] not in ("qsr",):
        parts.append(f"{size:g} {r['unit']}")
    return re.sub(r"\s+", " ", " ".join(p for p in parts if p)).strip()


def _product(r: dict, alts: dict[str, dict]) -> Product:
    fried = {"Y": True, "N": False}.get(r["fried"])
    return Product(
        name=shopper_name(r), category=_category(r["category"], r["craving"]),
        form=r["limit_set"] or ("liquid" if r["unit"] == "ml" else "solid"),
        sugar_g=num(r["total_sugar_g"]), added_sugar_g=num(r["added_sugar_g"]),
        sodium_mg=num(r["sodium_mg"]), satfat_g=num(r["sat_fat_g"]), kcal=num(r["energy_kcal"]),
        serving=num(r["serving_g"]), pack=num(r["pack_size"]), price_inr=num(r["mrp_inr"]),
        barcode=r["barcode"], source="team", team_id=r["ID"], confidence=r["confidence"],
        group=r["poshanscan_group"], fried=fried, craving=r["craving"], swaps=_swaps(r, alts),
        aliases=[a.lower() for a in {f"{r['brand']} {r['product_name']}", r["product_name"], r["display_name"],
                                     f"{r['product_name']} {r['variant']}".strip()} if a.strip()],
    )


def _load():
    alt_rows = _rows("alternatives.csv")
    alts = {r["ID"]: r for r in alt_rows}
    products = [_product(r, alts) for r in _rows("products.csv")]
    alternatives = [_alternative(r) for r in alt_rows
                    if any(r[k] for k in ("total_sugar_g", "added_sugar_g", "sodium_mg", "sat_fat_g"))]
    return products, alternatives


PRODUCTS, ALTERNATIVES = _load()
BY_ID = {p.team_id: p for p in PRODUCTS + ALTERNATIVES}
BY_BARCODE: dict[str, Product] = {}
for _p in ALTERNATIVES + PRODUCTS:  # products win when an alternative shares a barcode
    if _p.barcode:
        BY_BARCODE[_p.barcode] = _p


def by_barcode(code: str) -> Product | None:
    return BY_BARCODE.get(code)


def search(text: str, limit: int = 10) -> list[tuple[Product, float]]:
    q = tokens(text)
    if not q:
        return []
    scored = []
    for p in PRODUCTS + ALTERNATIVES:
        s = max(match_score(q, tokens(n)) for n in [p.name] + p.aliases)
        if s > 0:
            scored.append((p, s))
    scored.sort(key=lambda x: -x[1])
    return scored[:limit]


def nudges() -> dict:
    path = TEAM_DIR / "nudges.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"templates": {}, "groups": {}}
