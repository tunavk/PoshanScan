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
    _db.commit()


def log(u: str, kind: str, product: str = "", nutrient: str = "", swap: str = "", detail: str = ""):
    _db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?)",
                (time.time(), u, kind, product, nutrient or "", swap, detail))
    _db.commit()


def high_count_this_week(u: str, nutrient: str) -> int:
    """How many different products high in `nutrient` the user checked in the last 7 days.
    The same product on the same day counts once, so re-scanning one pack isn't a 'pattern'."""
    q = f"""SELECT COUNT(DISTINCT product || date(ts, 'unixepoch')) FROM events
            WHERE uid=? AND nutrient=? AND ts>? AND kind IN ({",".join("?" * len(CHECK_KINDS))})"""
    return _db.execute(q, (u, nutrient, time.time() - WEEK, *CHECK_KINDS)).fetchone()[0]


def week_summary(u: str) -> dict:
    since = time.time() - WEEK
    marks = ",".join("?" * len(CHECK_KINDS))
    # Same product on the same day counts once, matching high_count_this_week.
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
