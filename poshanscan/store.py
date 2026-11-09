"""SQLite storage. Phone numbers are stored only as salted hashes (DPDP Act: data minimisation)."""
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(os.getenv("POSHAN_DB", Path(__file__).parent.parent / "poshanscan.db"))
SALT = os.getenv("POSHAN_SALT", "change-me-in-production")

_db = sqlite3.connect(DB_PATH, check_same_thread=False)
_db.executescript("""
CREATE TABLE IF NOT EXISTS users (
    uid TEXT PRIMARY KEY, consented INTEGER DEFAULT 0, lang TEXT DEFAULT 'en',
    state TEXT DEFAULT '{}', created REAL
);
CREATE TABLE IF NOT EXISTS events (
    ts REAL, uid TEXT, kind TEXT, product TEXT, nutrient TEXT, swap TEXT, detail TEXT
);
CREATE INDEX IF NOT EXISTS events_uid_ts ON events (uid, ts);
CREATE TABLE IF NOT EXISTS intake (
    ts REAL, uid TEXT, product TEXT, grp TEXT, high_sugar INTEGER, high_salt INTEGER,
    sugar_tsp REAL, salt_g REAL, clean INTEGER
);
CREATE INDEX IF NOT EXISTS intake_uid_ts ON intake (uid, ts);
""")

WEEK = 7 * 24 * 3600
# Events that mean "the user checked a product" (as opposed to consent, feedback, ...)
CHECK_KINDS = ("barcode_scan", "name_lookup", "label_scan", "front_scan", "list_pick", "list_item")  # list_pick: older rows


def uid(phone: str) -> str:
    return hashlib.sha256((SALT + phone).encode()).hexdigest()[:24]


def get_user(u: str) -> dict:
    row = _db.execute("SELECT consented, lang, state FROM users WHERE uid=?", (u,)).fetchone()
    if not row:
        _db.execute("INSERT INTO users (uid, created) VALUES (?, ?)", (u, time.time()))
        _db.commit()
        return {"new": True, "consented": False, "lang": "en", "state": {}}
    return {"new": False, "consented": bool(row[0]), "lang": row[1], "state": json.loads(row[2])}


def update_user(u: str, **fields):
    if "state" in fields:
        fields["state"] = json.dumps(fields["state"])
    sets = ", ".join(f"{k}=?" for k in fields)
    _db.execute(f"UPDATE users SET {sets} WHERE uid=?", (*fields.values(), u))
    _db.commit()


def delete_user(u: str):
    _db.execute("DELETE FROM users WHERE uid=?", (u,))
    _db.execute("DELETE FROM events WHERE uid=?", (u,))
    _db.execute("DELETE FROM intake WHERE uid=?", (u,))
    _db.commit()


def log(u: str, kind: str, product: str = "", nutrient: str = "", swap: str = "", detail: str = ""):
    _db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?)",
                (time.time(), u, kind, product, nutrient or "", swap, detail))
    _db.commit()


def week_summary(u: str) -> dict:
    since = time.time() - WEEK
    marks = ",".join("?" * len(CHECK_KINDS))
    # Same product on the same day counts once, so re-scanning one pack isn't counted twice.
    checked = _db.execute(f"""SELECT COUNT(DISTINCT product || date(ts, 'unixepoch')) FROM events
                              WHERE uid=? AND ts>? AND kind IN ({marks})""",
                          (u, since, *CHECK_KINDS)).fetchone()[0]
    high = dict(_db.execute(f"""SELECT nutrient, COUNT(DISTINCT product || date(ts, 'unixepoch')) FROM events
                                WHERE uid=? AND ts>? AND nutrient!='' AND kind IN ({marks})
                                GROUP BY nutrient""", (u, since, *CHECK_KINDS)).fetchall())
    feedback = dict(_db.execute("""SELECT detail, COUNT(*) FROM events
                                   WHERE uid=? AND ts>? AND kind='feedback' GROUP BY detail""",
                                (u, since)).fetchall())
    return {"checked": checked, "high": high,
            "switch": feedback.get("switch", 0), "answered": sum(feedback.values())}


# ---------- daily picks, for the team's "My Day" nudges ----------
# One row per single product check (not shopping-list items: a list is a plan, not what was eaten).
# Days are local calendar days.

def log_intake(u: str, product: str, grp: str, high_sugar: bool, high_salt: bool,
               sugar_tsp: float, salt_g: float, clean: bool) -> None:
    _db.execute("INSERT INTO intake VALUES (?,?,?,?,?,?,?,?,?)",
                (time.time(), u, product, grp, int(high_sugar), int(high_salt), sugar_tsp, salt_g, int(clean)))
    _db.commit()


def today(u: str) -> dict:
    """Totals for today so far, including the pick just logged."""
    r = _db.execute("""SELECT COUNT(*), COALESCE(SUM(high_sugar),0), COALESCE(SUM(high_salt),0),
                              COALESCE(SUM(sugar_tsp),0), COALESCE(SUM(salt_g),0), COALESCE(SUM(clean),0)
                       FROM intake WHERE uid=? AND date(ts,'unixepoch','localtime') = date('now','localtime')""",
                    (u,)).fetchone()
    return dict(zip(("picks", "high_sugar", "high_salt", "sugar_tsp", "salt_g", "clean"), r))


def group_today(u: str, grp: str) -> int:
    return _db.execute("""SELECT COUNT(*) FROM intake WHERE uid=? AND grp=?
                          AND date(ts,'unixepoch','localtime') = date('now','localtime')""", (u, grp)).fetchone()[0]


def group_streak(u: str, grp: str) -> int:
    """Consecutive days, ending today, with at least one pick in this group."""
    days = {r[0] for r in _db.execute("""SELECT DISTINCT CAST(julianday(date(ts,'unixepoch','localtime')) AS INTEGER)
                                          FROM intake WHERE uid=? AND grp=?""", (u, grp))}
    today_n = _db.execute("SELECT CAST(julianday(date('now','localtime')) AS INTEGER)").fetchone()[0]
    n = 0
    while today_n - n in days:
        n += 1
    return n
