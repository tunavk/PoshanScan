"""Checks for the team's food database integration (data/team).

    .venv/bin/python tests/test_team_db.py
"""
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ["POSHAN_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")
os.environ.pop("ANTHROPIC_API_KEY", None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from poshanscan import bot, products, store, team  # noqa: E402
from poshanscan.model import Product  # noqa: E402
from poshanscan.scoring import SETTINGS, THRESHOLDS, score  # noqa: E402

products._open_food_facts = lambda code: None

failures = 0


def check(cond, what):
    global failures
    print(("  ✅ " if cond else "  ❌ ") + what)
    failures += not cond


def send(phone, text):
    out = "\n---\n".join(r.text for r in bot.handle(bot.Incoming(phone=phone, text=text)))
    print(f"\n👤 {text}\n🤖 {out}")
    return out


def item(sugar=None, added=None, sodium=None, satfat=None, form="solid"):
    return Product(name="Test", category="any", form=form, sugar_g=sugar, added_sugar_g=added,
                   sodium_mg=sodium, satfat_g=satfat, kcal=None, serving=30)


print("=== Data loaded from the spreadsheet import")
check(len(team.PRODUCTS) == 403, f"403 team products ({len(team.PRODUCTS)})")
check(len(team.ALTERNATIVES) > 300, f"healthy alternatives with nutrition ({len(team.ALTERNATIVES)})")
check(THRESHOLDS == SETTINGS["limits"] and THRESHOLDS["solid"]["sugar"] == 10, "limits come from the Read Me yellow cells")
bad = [p.name for p in team.PRODUCTS if any(w in p.name.lower() for w in ("slum", "not stated", "presumed", "street /"))]
check(not bad, f"no research notes in product names {bad[:3]}")

print("\n=== Scoring follows the team's rules")
check(not score(item(sugar=10, sodium=0, satfat=0)).is_high, "exactly at the limit: no warning (strictly greater)")
check(score(item(sugar=10.1, sodium=0, satfat=0)).highs == ["sugar"], "just over the limit: warning")
check(not score(item(sugar=30, added=2, sodium=0, satfat=0)).is_high, "added sugar is used when given (milk sugar isn't)")
check(score(item(sugar=30, sodium=0, satfat=0)).is_high, "total sugar is used when added sugar is blank")
grades = [score(item(sugar=s, sodium=0, satfat=0)).grade for s in (2.5, 5, 10, 20, 20.1)]
check(grades == list("ABCDE"), f"grade bands A..E at 0.25/0.5/1/2 of the limit ({''.join(grades)})")
check(score(item()).grade == "?", "no values: grade ?")
v = score(item(sugar=25, sodium=900, satfat=1))
check(v.highs == ["sugar", "salt"] and v.grade == "E", "every high nutrient listed, worst first")

print("\n=== Team product, team swaps and MORE")
A = "whatsapp:+910000000101"
send(A, "yes")
out = send(A, "good day")
check("Grade E" in out and "HIGH IN SUGAR" in out and "HIGH IN SATURATED FAT" in out, "grade + every HIGH label")
check("Amla (₹6 a serving, grade A)" in out and "Saves 1.7 tsp sugar" in out, "team's Same craving swap with price and saving")
check("Reply *MORE*" in out, "offers MORE")
out = send(A, "more")
check("Cheaper" in out and "Best for health" in out, "MORE shows the Cheaper and Best for health cards")
out = send(A, "pepsi")
check("added sugar" in out, "says 'added sugar' when the label gives it")

print("\n=== Clean, partial and no-data products")
out = send(A, "diet coke")
check("Grade A" in out and "Nice pick" in out, "clean pick: grade + team praise")
out = send(A, "britannia english tea cake")
check("don't have its nutrition label" in out, "price-only product: honest no-data reply")
partial = next(p for p in team.PRODUCTS if p.barcode and not score(p).is_high
               and not score(p).no_data and len(score(p).grades) < 3)
out = send(A, partial.barcode)
check("check the pack" in out, f"clean but incomplete data says so ({partial.name})")

print("\n=== Daily reminders (team Nudge Messages)")
B = "whatsapp:+910000000102"
send(B, "yes")
send(B, "maaza")
out = send(B, "pepsi")
check("second high sugar item today" in out and "of 6 teaspoons" in out, "2nd sugary pick: running teaspoons")
uid = store.uid(B)
for days_ago in (1, 2):  # sugary picks on the two previous days
    store._db.execute("INSERT INTO intake VALUES (?,?,?,?,?,?,?,?,?)",
                      (time.time() - days_ago * 86400, uid, "Old pick", "salty", 0, 1, 0, 1.0, 0))
store._db.commit()
out = send(B, "kurkure")
check("3 days in a row with a salty pick" in out, "3-day streak message")
send(B, "hindi")
out = send(B, "frooti")
check("तीसरी" in out, "Hindi reminder uses the feminine ordinal")

print("\n=== Shopping lists")
C = "whatsapp:+910000000103"
send(C, "yes")
out = send(C, "oreo, diet coke, britannia english tea cake")
check("No label data yet: Britannia English Tea Cake" in out, "no-data item isn't called 'fine'")
check("Look fine: Coca-Cola Diet Coke" in out, "clean item listed as fine")
check("📅" not in out, "lists don't count as today's picks (no reminders)")

print(f"\n{'All checks passed' if not failures else f'{failures} check(s) FAILED'}")
sys.exit(1 if failures else 0)
