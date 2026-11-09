"""Read-only product catalogue imported from Open Food Facts India (see scripts/import_off.py)."""
import sqlite3
from pathlib import Path

from .model import Product, match_score, tokens

CATALOG_PATH = Path(__file__).parent / "data" / "catalog.db"

_db = None


def _conn():
    global _db
    if _db is None and CATALOG_PATH.exists():
        _db = sqlite3.connect(f"file:{CATALOG_PATH}?mode=ro", uri=True, check_same_thread=False)
        _db.row_factory = sqlite3.Row
    return _db


def _product(r) -> Product:
    return Product(
        name=r["name"], category=r["category"], form=r["form"],
        sugar_g=r["sugar_g"], sodium_mg=r["sodium_mg"], satfat_g=r["satfat_g"], kcal=r["kcal"],
        serving=r["serving"] or (r["pack"] if r["pack"] and r["pack"] <= 100 else None),
        pack=r["pack"], barcode=r["barcode"], source="imported",
    )


def by_barcode(code: str) -> Product | None:
    db = _conn()
    if not db:
        return None
    r = db.execute("SELECT * FROM products WHERE barcode=?", (code,)).fetchone()
    return _product(r) if r else None


def search(text: str, limit: int = 3) -> list[tuple[Product, float]]:
    """Best catalogue matches for a product name, best first, with a 0..1 score."""
    db = _conn()
    q = tokens(text)
    if not db or not q:
        return []
    fts = " OR ".join(f'"{w}"*' if len(w) >= 4 else f'"{w}"' for w in q)
    rows = db.execute(
        """SELECT p.* FROM products_fts f JOIN products p ON p.barcode = f.barcode
           WHERE products_fts MATCH ? ORDER BY bm25(products_fts) LIMIT 40""", (fts,)).fetchall()
    scored = [(_product(r), match_score(q, tokens(r["brand"] + " " + r["name"])), r["popularity"] or 0)
              for r in rows]
    scored.sort(key=lambda x: (-x[1], -x[2]))
    return [(p, s) for p, s, _ in scored[:limit]]


def size() -> int:
    db = _conn()
    return db.execute("SELECT COUNT(*) FROM products").fetchone()[0] if db else 0
