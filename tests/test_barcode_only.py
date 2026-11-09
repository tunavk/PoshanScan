"""Barcode-first mode: no ANTHROPIC_API_KEY. Real barcode decoding on generated images.

    .venv/bin/python tests/test_barcode_only.py
"""
import io
import os
import sys
import tempfile
from pathlib import Path

os.environ["POSHAN_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import zxingcpp  # noqa: E402
from PIL import Image  # noqa: E402

from poshanscan import bot, products, vision  # noqa: E402

products._open_food_facts = lambda code: None  # offline and repeatable


def barcode_photo(code: str) -> bytes:
    """A barcode on a cardboard-coloured background, slightly rotated, saved as a compressed JPEG
    (roughly what WhatsApp delivers)."""
    raw = memoryview(zxingcpp.create_barcode(code, zxingcpp.BarcodeFormat.EAN13).to_image(scale=4))
    img = Image.frombytes("L", (raw.shape[1], raw.shape[0]), raw.tobytes()).resize((raw.shape[1], 200))
    canvas = Image.new("RGB", (1200, 900), (210, 190, 160))
    canvas.paste(img.convert("RGB"), ((1200 - img.width) // 2, 350))
    out = io.BytesIO()
    canvas.rotate(4, fillcolor=(210, 190, 160)).save(out, "JPEG", quality=55)
    return out.getvalue()


def plain_photo() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (800, 600), (230, 120, 40)).save(out, "JPEG")
    return out.getvalue()


def send(text="", photo=None):
    replies = bot.handle(bot.Incoming(phone="whatsapp:+910000000009", text=text,
                                      images=[(photo, "image/jpeg")] if photo else []))
    out = "\n---\n".join(r.text for r in replies)
    print(f"\n👤 {text or '[photo]'}\n🤖 {out}")
    return out


failures = 0


def check(cond, what):
    global failures
    print(("  ✅ " if cond else "  ❌ ") + what)
    failures += not cond


PHOTO_WORDS = ("front", "nutrition table", "photo of your list", "AI service")

check(not vision.available(), "photo reading is off")
out = send("hi")
check("barcode" in out and not any(w in out for w in PHOTO_WORDS), "welcome only offers barcodes and typing")
out = send("yes")
check("barcode" in out and not any(w in out for w in PHOTO_WORDS), "ready message only offers barcodes and typing")
out = send("help")
check(not any(w in out for w in PHOTO_WORDS), "help doesn't mention photo features")

out = send(photo=barcode_photo("8901719134845"))
check("Parle-G" in out and "HIGH IN SUGAR" in out, "barcode photo of a curated product (Parle-G)")
out = send(photo=barcode_photo("8901725016296"))
check("Bourbon" in out and "HIGH IN" in out, "barcode photo of another curated product (Dark Fantasy Bourbon)")

catalogue_code = products.catalog._conn().execute(
    "SELECT barcode FROM products WHERE category='noodles' AND length(barcode)=13 ORDER BY popularity DESC LIMIT 1"
).fetchone()[0]
out = send(photo=barcode_photo(catalogue_code))
check("data: Open Food Facts" in out, f"barcode photo of a catalogue-only product ({catalogue_code})")

out = send(photo=barcode_photo("2000000000015"))
check("Try typing the product name" in out and "nutrition table" not in out,
      "unknown barcode: suggests typing the name, doesn't ask for label photos")
out = send(photo=plain_photo())
check("couldn't read a barcode" in out and "type the product name" in out, "photo without a barcode: helpful reply")
out = send("frooti, hide and seek, maggi")
check("Frooti" in out and "Maggi" in out, "typed list still works")

send("hindi")
out = send("help")
check("बारकोड" in out and "WEEK" in out and "सामने" not in out, "Hindi help is barcode-only too")

print(f"\n{'All checks passed' if not failures else f'{failures} check(s) FAILED'}")
sys.exit(1 if failures else 0)
