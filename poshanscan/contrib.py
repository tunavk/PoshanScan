"""Products taught to the bot by shoppers (barcode + photo of the nutrition table).

Only the numbers read from the label are kept, never the photos. One shopper's reading is
shown to everyone as "not yet confirmed"; once two different shoppers' readings agree it is
"confirmed". Contributions are keyed by barcode, or by product name when there was no barcode.
"""
import time

from . import quality
from .model import Product, match_score, tokens
from .store import _db

_db.executescript("""
CREATE TABLE IF NOT EXISTS contributions (
    key TEXT, barcode TEXT, uid TEXT, ts REAL, name TEXT, category TEXT, form TEXT,
    sugar_g REAL, sodium_mg REAL, satfat_g REAL, kcal REAL, serving REAL, pack REAL
);
CREATE INDEX IF NOT EXISTS contributions_key ON contributions (key);
""")

FIELDS = ("sugar_g", "sodium_mg", "satfat_g", "kcal", "serving", "pack")


def key_for(barcode: str, name: str) -> str:
    return barcode or "name:" + " ".join(sorted(tokens(name)))


def save(uid: str, p: Product) -> str:
    """Store one shopper's reading. A shopper re-sending the same product replaces their earlier reading."""
    key = key_for(p.barcode, p.name)
    _db.execute("DELETE FROM contributions WHERE key=? AND uid=?", (key, uid))
    _db.execute("INSERT INTO contributions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (key, p.barcode, uid, time.time(), p.name, p.category, p.form,
                 p.sugar_g, p.sodium_mg, p.satfat_g, p.kcal, p.serving, p.pack))
    _db.commit()
    return key


def rename(key: str, uid: str, name: str, category: str) -> None:
    """Add the product's name once the shopper sends a photo of the front."""
    _db.execute("UPDATE contributions SET name=?, category=? WHERE key=? AND uid=?", (name, category, key, uid))
    _db.commit()


def product_for(key: str) -> Product | None:
    rows = _db.execute("""SELECT uid, name, category, form, barcode, sugar_g, sodium_mg, satfat_g, kcal, serving, pack
                          FROM contributions WHERE key=? ORDER BY ts DESC""", (key,)).fetchall()
    if not rows:
        return None
    readings = [dict(zip(("uid", "name", "category", "form", "barcode") + FIELDS, r)) for r in rows]
    chosen, source = readings[0], "contributed"
    for i, a in enumerate(readings):  # newest pair of different shoppers that agree
        match = next((b for b in readings[i + 1:] if b["uid"] != a["uid"] and quality.agree(a, b)), None)
        if match:
            chosen, source = a, "confirmed"
            break
    name = next((r["name"] for r in readings if r["name"]), "Unnamed product")
    category = next((r["category"] for r in readings if r["category"] not in ("", "any")), "any")
    return Product(name=name, category=category, form=chosen["form"],
                   sugar_g=chosen["sugar_g"], sodium_mg=chosen["sodium_mg"], satfat_g=chosen["satfat_g"],
                   kcal=chosen["kcal"], serving=chosen["serving"], pack=chosen["pack"],
                   barcode=chosen["barcode"] or "", source=source)


def by_barcode(code: str) -> Product | None:
    return product_for(code)


def search(text: str, limit: int = 3) -> list[tuple[Product, float]]:
    q = tokens(text)
    if not q:
        return []
    keys = _db.execute("SELECT key, MAX(name) FROM contributions GROUP BY key").fetchall()
    scored = sorted(((k, match_score(q, tokens(n or ""))) for k, n in keys), key=lambda x: -x[1])
    out = []
    for k, s in scored[:limit]:
        p = product_for(k)
        if p and s > 0:
            out.append((p, s))
    return out


def anonymise(uid: str) -> None:
    """On STOP: keep the label numbers (product facts, useful to others) but drop the link to the person."""
    _db.execute("UPDATE contributions SET uid='deleted-' || hex(randomblob(8)) WHERE uid=?", (uid,))
    _db.commit()
