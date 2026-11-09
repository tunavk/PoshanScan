"""Build poshanscan/data/catalog.db from Open Food Facts' products sold in India.

    .venv/bin/pip install -r scripts/requirements-import.txt
    .venv/bin/python scripts/import_off.py                    # downloads the India rows (slow: reads a ~8 GB file)
    .venv/bin/python scripts/import_off.py --parquet off_india.parquet   # reuse an earlier download

Every product goes through the same checks as live lookups (poshanscan/quality.py).
Rejected products and the reasons are counted in poshanscan/data/catalog_report.txt.
"""
import argparse
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from poshanscan import quality  # noqa: E402
from poshanscan.products import category_from_tags, is_liquid  # noqa: E402

REMOTE = "https://huggingface.co/datasets/openfoodfacts/product-database/resolve/main/food.parquet"
COLUMNS = """code, brands, product_name, categories_tags, product_quantity, product_quantity_unit,
             serving_quantity, nutriments, unique_scans_n, obsolete"""
OUT = ROOT / "poshanscan" / "data" / "catalog.db"
REPORT = ROOT / "poshanscan" / "data" / "catalog_report.txt"


def number(v):
    try:
        m = re.search(r"\d+(\.\d+)?", str(v).replace(",", "."))
        return float(m.group()) if m else None
    except (TypeError, ValueError):
        return None


def pick_name(names) -> str:
    if not names:
        return ""
    by_lang = {n["lang"]: n["text"] for n in names if n and n.get("text")}
    return (by_lang.get("main") or by_lang.get("en") or next(iter(by_lang.values()), "")).strip()


def convert(row: dict) -> tuple[dict | None, str]:
    """One Open Food Facts row -> our catalogue row, or (None, reason it was rejected)."""
    code = re.sub(r"\D", "", row["code"] or "")
    if not 8 <= len(code) <= 14:
        return None, "no valid barcode"
    if row["obsolete"]:
        return None, "product discontinued"
    name = re.sub(r"\b\d{8,14}\b", "", pick_name(row["product_name"])).strip(" -,")  # some names include the barcode
    if not name:
        return None, "no product name"
    n = {x["name"]: x["100g"] for x in (row["nutriments"] or []) if x and x.get("100g") is not None}
    sodium_g = n.get("sodium")
    if sodium_g is None and n.get("salt") is not None:
        sodium_g = n["salt"] / 2.5
    sodium = sodium_g * 1000 if sodium_g is not None else None
    sugar, satfat, kcal = n.get("sugars"), n.get("saturated-fat"), n.get("energy-kcal")
    issues = quality.problems(sugar, sodium, satfat, kcal, n.get("fat"), n.get("carbohydrates"), n.get("proteins"))
    if issues:
        reason = issues[0]
        return None, "missing sugar, sodium or saturated fat" if reason.startswith("missing") else re.sub(r"[\d.]+", "N", reason)
    tags = list(row["categories_tags"] or [])
    category = category_from_tags(tags)
    liquid = is_liquid(tags, row["product_quantity_unit"], category)
    brand = (row["brands"] or "").split(",")[0].strip()
    full_name = name if brand.lower() in name.lower() else f"{brand} {name}".strip()
    return {
        "barcode": code, "name": full_name[:120], "brand": brand, "category": category,
        "form": "liquid" if liquid else "solid",
        "pack": number(row["product_quantity"]), "serving": number(row["serving_quantity"]),
        "sugar_g": round(sugar, 2), "sodium_mg": round(sodium, 1), "satfat_g": round(satfat, 2),
        "kcal": round(kcal, 1) if kcal is not None else None,
        "popularity": row["unique_scans_n"] or 0,
    }, "kept"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", help="a local extract (from an earlier run) instead of downloading")
    args = ap.parse_args()

    con = duckdb.connect()
    if args.parquet:
        source = f"read_parquet('{args.parquet}')"
        where = "WHERE list_contains(countries_tags, 'en:india')"
    else:
        con.execute("INSTALL httpfs; LOAD httpfs;")
        print("Reading India rows from Open Food Facts (this can take 30+ minutes)...")
        source, where = f"read_parquet('{REMOTE}')", "WHERE list_contains(countries_tags, 'en:india')"
    rel = con.execute(f"SELECT {COLUMNS} FROM {source} {where}")
    cols = [d[0] for d in rel.description]

    reasons, kept = Counter(), {}
    while batch := rel.fetchmany(5000):
        for values in batch:
            out, why = convert(dict(zip(cols, values)))
            reasons[why] += 1
            if out and (out["barcode"] not in kept or out["popularity"] > kept[out["barcode"]]["popularity"]):
                kept[out["barcode"]] = out

    OUT.unlink(missing_ok=True)
    db = sqlite3.connect(OUT)
    db.executescript("""
        CREATE TABLE products (barcode TEXT PRIMARY KEY, name TEXT, brand TEXT, category TEXT, form TEXT,
            pack REAL, serving REAL, sugar_g REAL, sodium_mg REAL, satfat_g REAL, kcal REAL, popularity INTEGER);
        CREATE VIRTUAL TABLE products_fts USING fts5(barcode UNINDEXED, text);
    """)
    fields = ["barcode", "name", "brand", "category", "form", "pack", "serving",
              "sugar_g", "sodium_mg", "satfat_g", "kcal", "popularity"]
    db.executemany(f"INSERT INTO products VALUES ({','.join('?' * len(fields))})",
                   [tuple(r[f] for f in fields) for r in kept.values()])
    db.executemany("INSERT INTO products_fts VALUES (?, ?)",
                   [(r["barcode"], f"{r['brand']} {r['name']}") for r in kept.values()])
    db.commit()

    total = sum(reasons.values())
    cats = Counter(r["category"] for r in kept.values())
    lines = [f"Open Food Facts India import: {total} rows read, {len(kept)} products kept", "",
             "Rejected (first problem found):"]
    lines += [f"  {n:6d}  {why}" for why, n in reasons.most_common() if why != "kept"]
    lines += ["", "Kept, by category:"] + [f"  {n:6d}  {c}" for c, n in cats.most_common()]
    REPORT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nWrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
