"""End-to-end checks of the photo flows with canned photo readings (no API key needed).

    .venv/bin/python tests/test_photo_flows.py

Each fake "photo" is a short byte string. FAKE_PHOTOS says what Claude would read in it,
and photos starting with BARCODE: stand for a readable barcode.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ["POSHAN_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-not-used")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from poshanscan import bot, products, vision  # noqa: E402

NEW_CODE = "2000000000015"  # in-store code range: not a real product anywhere


def front(brand, name, variant="", category="any", pack=None, liquid=False):
    return {"kind": "product_photo", "items": [], "label": _empty_label(),
            "product": {"brand": brand, "name": name, "variant": variant, "pack_size": pack,
                        "category": category, "is_liquid": liquid}}


def label(sugar, sodium, satfat, kcal=None, fat=None, carbs=None, protein=None, per="100g", serving=None):
    return {"kind": "nutrition_label", "items": [], "product": _empty_product(),
            "label": {"product_name": "", "per": per, "sugar_g": sugar, "sodium_mg": sodium, "salt_g": None,
                      "satfat_g": satfat, "fat_g": fat, "carbs_g": carbs, "protein_g": protein,
                      "kcal": kcal, "serving_size": serving}}


def _empty_label():
    return label(None, None, None, per="unknown")["label"]


def _empty_product():
    return {"brand": "", "name": "", "variant": "", "pack_size": None, "category": "any", "is_liquid": False}


FAKE_PHOTOS = {
    b"crunchies-front": front("Zzyzx", "Crunchies", "Masala", "chips", 40),
    b"crunchies-label": label(2.0, 820, 9.5, kcal=530, fat=32, carbs=55, protein=6, serving=40),
    b"crunchies-label-2": label(2.1, 800, 9.4, kcal=530, fat=32, carbs=55, protein=6, serving=40),
    b"crunchies-label-bad": label(2.0, 120000, 9.5),
    b"maggi-front": front("Maggi", "2-Minute Noodles", "Masala", "noodles", 70),
    b"lays-front": front("Lay's", "Potato Chips", "", "chips", 50),
    b"blur": {"kind": "other", "items": [], "product": _empty_product(), "label": _empty_label()},
}

vision.read_photo = lambda image, mime: FAKE_PHOTOS.get(image)
products._open_food_facts = lambda code: None  # no live lookups: keep the test offline and repeatable
bot._decode_barcode = lambda image: image.split(b":")[1].decode() if image.startswith(b"BARCODE:") else None


def send(phone, text="", *photos):
    replies = bot.handle(bot.Incoming(phone=phone, text=text, images=[(p, "image/jpeg") for p in photos]))
    out = "\n---\n".join(r.text for r in replies)
    print(f"\n👤 {phone[-4:]}: {text or ''} {' '.join(p.decode() for p in photos)}\n🤖 {out}")
    return out


def check(cond, what):
    print(("  ✅ " if cond else "  ❌ ") + what)
    if not cond:
        global failures
        failures += 1


failures = 0
A, B, C = "whatsapp:+910000000001", "whatsapp:+910000000002", "whatsapp:+910000000003"
for phone in (A, B, C):
    send(phone, "yes")

print("\n=== 1. Unknown barcode -> asked to teach -> front + label together")
out = send(A, "", f"BARCODE:{NEW_CODE}".encode())
check("Help me learn it" in out, "asks for front + nutrition table")
out = send(A, "", b"crunchies-front", b"crunchies-label")
check("HIGH IN" in out and "saved this product" in out, "answers from the label straight away and saves it")
check("read from your photo" in out, "says the numbers came from their photo")

print("\n=== 2. Someone else scans the same barcode")
out = send(B, "", f"BARCODE:{NEW_CODE}".encode())
check("Zzyzx Crunchies" in out and "not yet confirmed" in out, "gets the taught product, marked unconfirmed")

print("\n=== 3. A second shopper's label agrees -> confirmed")
send(B, "", f"BARCODE:{NEW_CODE}".encode(), b"crunchies-label-2")
out = send(C, "", f"BARCODE:{NEW_CODE}".encode())
check("from shoppers' photos" in out, "third shopper sees it as confirmed")

print("\n=== 4. Implausible label numbers are rejected")
out = send(C, "", b"crunchies-label-bad")
check("couldn't read the nutrition table" in out, "asks for a clearer photo instead of warning")

print("\n=== 5. Front-of-pack photo, clear match")
out = send(A, "", b"maggi-front")
check("Maggi" in out and "HIGH IN SALT" in out, "recognises Maggi and warns about salt")
check("Not the right product" in out, "offers a way out if it's wrong")

print("\n=== 5b. Front-of-pack photos of products only in the Open Food Facts catalogue")
FAKE_PHOTOS[b"hideseek-front"] = front("Parle", "Hide & Seek", "Chocolate Chip Cookies", "biscuit", 100)
out = send(B, "", b"hideseek-front")
check("hide" in out.lower() and "seek" in out.lower() and "HIGH IN" in out, "recognises Parle Hide & Seek from the catalogue")
FAKE_PHOTOS[b"frooti-front"] = front("Frooti", "Mango Drink", "", "juice_drink", 200, liquid=True)
send(B, "hindi")
out = send(B, "", b"frooti-front")
check("Frooti" in out and "चीनी ज़्यादा" in out, "recognises Frooti and warns about sugar, in Hindi")
send(B, "english")

print("\n=== 6. Front-of-pack photo, ambiguous -> which one?")
out = send(A, "", b"lays-front")
check("Which one is it?" in out, "asks which variant")
lays_options = [line for line in out.splitlines() if line.startswith("*") and "Lay" in line]
check(len(lays_options) >= 2, f"offers several Lay's variants ({len(lays_options)})")
out = send(A, "2")
check("HIGH IN" in out and "Lay" in out, "answers for the chosen variant")

print("\n=== 7. Front photo of an unknown product -> teach by name, no barcode")
front_bytes = b"gulab-front"
FAKE_PHOTOS[front_bytes] = front("Qwerty Foods", "Gulab Jamun Mix", "", "chocolate", 200)
out = send(B, "", front_bytes)
check("don't know" in out and "Gulab Jamun Mix" in out, "says it doesn't know it, asks for the label")
FAKE_PHOTOS[b"gulab-label"] = label(45.0, 300, 6.0, kcal=420, fat=12, carbs=72, protein=7)
out = send(B, "", b"gulab-label")
check("HIGH IN SUGAR" in out and "saved" in out, "warns and saves under the name")
out = send(C, "", front_bytes)
check("Gulab Jamun Mix" in out and "not yet confirmed" in out, "next shopper's front photo finds it")

print("\n=== 8. Label first (with barcode), front afterwards")
code2 = "2000000000022"
send(C, "", f"BARCODE:{code2}".encode())
FAKE_PHOTOS[b"juice-label"] = label(12.0, 20, 0.0, kcal=50, fat=0, carbs=12.5, protein=0.2, per="100ml", serving=200)
out = send(C, "", b"juice-label")
check("front* of the pack" in out, "asks for the front so others can find it")
FAKE_PHOTOS[b"juice-front"] = front("Fruity", "Mango Drink", "", "juice_drink", 200, liquid=True)
out = send(C, "", b"juice-front")
check("Saved as *Fruity Mango Drink*" in out, "names the saved product")
check(products.by_barcode(code2).name == "Fruity Mango Drink", "barcode now resolves to the named product")

print("\n=== 9. Skip, unreadable photo, STOP")
send(A, "", f"BARCODE:{'2000000000039'}".encode())
check("cancelled" in send(A, "skip"), "skip cancels the teach flow")
check("couldn't make out" in send(A, "", b"blur"), "unreadable photo gets a helpful reply")
send(B, "stop")
out = send(C, "", f"BARCODE:{NEW_CODE}".encode())
check("Zzyzx" in out, "product taught by a user who left is still available (anonymised)")

print(f"\n{'All checks passed' if not failures else f'{failures} check(s) FAILED'}")
sys.exit(1 if failures else 0)
