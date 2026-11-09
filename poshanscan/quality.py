"""Sanity checks for nutrition data from any source we don't control
(Open Food Facts imports, live lookups, shoppers' label photos).

Crowd-sourced data has real errors, e.g. Yippee noodles listed with 1,182 g sodium per 100 g
(a mg/g unit mix-up). A wrong warning is worse than no warning, so bad rows are rejected.
"""

def problems(sugar_g, sodium_mg, satfat_g, kcal=None, fat_g=None, carbs_g=None, protein_g=None) -> list[str]:
    """Empty list = looks plausible. Values are per 100 g / 100 ml."""
    out = []
    if sugar_g is None or sodium_mg is None or satfat_g is None:
        out.append("missing sugar, sodium or saturated fat")
        return out
    if not 0 <= sugar_g <= 100:
        out.append(f"sugar {sugar_g} g out of range")
    if not 0 <= satfat_g <= 100:
        out.append(f"saturated fat {satfat_g} g out of range")
    if not 0 <= sodium_mg <= 40_000:  # pure salt is ~39 g sodium per 100 g
        out.append(f"sodium {sodium_mg} mg out of range")
    if sugar_g + satfat_g + sodium_mg / 1000 > 105:
        out.append("components add up to more than 100 g")
    if fat_g is not None and satfat_g > fat_g + 0.5:
        out.append("saturated fat higher than total fat")
    if carbs_g is not None and sugar_g > carbs_g + 0.5:
        out.append("sugar higher than total carbohydrate")
    # Calories should roughly match 9 kcal/g fat + 4 kcal/g carbs and protein.
    if None not in (kcal, fat_g, carbs_g, protein_g) and kcal > 0:
        expected = 9 * fat_g + 4 * carbs_g + 4 * protein_g
        if abs(kcal - expected) > max(0.25 * kcal, 40):
            out.append(f"calories {kcal:.0f} don't match macros ({expected:.0f})")
    return out


def agree(a: dict, b: dict) -> bool:
    """Do two readings of the same label match? Used to confirm shoppers' contributions."""
    tolerance = {"sugar_g": 0.5, "satfat_g": 0.5, "sodium_mg": 50}
    for key, floor in tolerance.items():
        x, y = a.get(key), b.get(key)
        if x is None or y is None:
            return False
        if abs(x - y) > max(floor, 0.1 * max(x, y)):
            return False
    return True
