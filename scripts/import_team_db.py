"""Import the team's food database spreadsheet into the files the bot reads.

    .venv/bin/pip install -r scripts/requirements-import.txt
    .venv/bin/python scripts/import_team_db.py "path/to/PoshanScan food database v2.xlsx"

Writes poshanscan/data/team/:
    products.csv      Products sheet: 403 packaged, QSR and street items with three swaps each
    alternatives.csv  Healthy Alternatives sheet: the swap pool (also scannable / searchable)
    settings.json     the yellow cells on "Read Me": warning limits, daily limits, grade bands
    nudges.json       the Nudge Messages templates and group words

Re-run it whenever the team edits the spreadsheet. The bot needs no spreadsheet library at runtime.
"""
import csv
import json
import re
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "poshanscan" / "data" / "team"

PRODUCT_COLUMNS = [
    "ID", "barcode", "brand", "product_name", "variant", "display_name", "category", "subcategory",
    "swap_category", "craving", "poshanscan_group", "limit_set", "unit", "pack_size", "serving_g",
    "mrp_inr", "price_per_serving", "energy_kcal", "total_sugar_g", "added_sugar_g", "sat_fat_g",
    "sodium_mg", "total_fat_g", "carbs_g", "protein_g", "fried", "confidence", "data_status",
    "swap_name", "cheaper_swap_name",
] + [f"s{i}_{f}" for i in (1, 2, 3) for f in (
    "label", "alt_id", "alt_name", "serving", "price_per_serving", "price_diff", "grade",
    "sugar_saved_tsp", "salt_saved_g", "reason")]

ALT_COLUMNS = [
    "ID", "barcode", "alt_name", "brand_or_outlet", "alt_label", "alt_type", "craving", "replaces",
    "serving_size", "unit", "serving_description", "pack_size", "pack_price_inr", "price_per_serving_inr",
    "price_type", "energy_kcal", "total_sugar_g", "added_sugar_g", "sat_fat_g", "sodium_mg",
    "total_fat_g", "carbs_g", "protein_g", "natural_note", "use_note", "status", "reason_line", "confidence",
]


def sheet_rows(ws) -> list[dict]:
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    return [dict(zip(header, r)) for r in rows[1:] if r and r[0]]


def clean(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.4f}".rstrip("0").rstrip(".")
    return str(v).strip()


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(columns)
        for r in rows:
            w.writerow([clean(r.get(c)) for c in columns])


def read_settings(ws) -> dict:
    """The yellow cells on Read Me, found by their row labels (so moving rows doesn't break it)."""
    rows = [r for r in ws.iter_rows(values_only=True)]
    label = {str(r[0]).strip(): r for r in rows if r and r[0]}

    def find(prefix):
        for k, r in label.items():
            if k.lower().startswith(prefix.lower()):
                return r
        raise KeyError(f"Read Me row starting with {prefix!r} not found")

    sugar, sodium, satfat = find("Added sugar (g)"), find("Sodium (mg)"), find("Saturated fat (g)")
    bands = {g: float(label[g][1]) for g in ("A", "B", "C", "D")}  # grade rows are labelled by the bare letter
    return {
        "limits": {
            "solid": {"sugar": float(sugar[1]), "salt": float(sodium[1]), "satfat": float(satfat[1])},
            "liquid": {"sugar": float(sugar[2]), "salt": float(sodium[2]), "satfat": float(satfat[2])},
        },
        "daily": {"sugar_g": float(find("Added sugar, daily limit")[1]),
                  "salt_g": float(find("Salt, daily limit")[1])},
        "sugar_per_tsp_g": float(find("Sugar in one teaspoon")[1]),
        "salt_per_sodium": float(find("Salt from sodium")[1]),
        "grade_bands": bands,
    }


def read_nudges(ws) -> dict:
    """Template rows sit between the "key" header and the "Ordinals" heading; group words after "group key"."""
    templates, groups, section = {}, {}, None
    for r in ws.iter_rows(values_only=True):
        first = str(r[0]).strip() if r and r[0] else ""
        if first == "key":
            section = "templates"
        elif first.startswith("Ordinals"):
            section = None
        elif first == "group key":
            section = "groups"
        elif first.startswith("Which message wins"):
            section = None
        elif section == "templates" and re.fullmatch(r"[a-z_0-9]+", first) and r[1]:
            templates[first] = str(r[1]).strip()
        elif section == "groups" and first and r[1] and r[2]:
            groups[first] = {"word": str(r[1]).strip(), "taste": str(r[2]).strip()}
    return {"templates": templates, "groups": groups}


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    wb = openpyxl.load_workbook(sys.argv[1], data_only=True)
    OUT.mkdir(parents=True, exist_ok=True)

    products = sheet_rows(wb["Products"])
    alternatives = sheet_rows(wb["Healthy Alternatives"])
    write_csv(OUT / "products.csv", products, PRODUCT_COLUMNS)
    write_csv(OUT / "alternatives.csv", alternatives, ALT_COLUMNS)
    settings = read_settings(wb["Read Me"])
    (OUT / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    nudges = read_nudges(wb["Nudge Messages"])
    (OUT / "nudges.json").write_text(json.dumps(nudges, indent=2, ensure_ascii=False) + "\n")

    print(f"products.csv      {len(products)} rows ({sum(1 for r in products if r.get('barcode'))} with barcodes)")
    print(f"alternatives.csv  {len(alternatives)} rows")
    print(f"settings.json     limits {settings['limits']}, daily {settings['daily']}")
    print(f"nudges.json       {len(nudges['templates'])} templates: {', '.join(nudges['templates'])}")


if __name__ == "__main__":
    main()
