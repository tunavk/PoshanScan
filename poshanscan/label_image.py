"""Render a Chile-style black octagon warning label as a PNG to send with the message."""
import math
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .scoring import Verdict

MEDIA_DIR = Path(__file__).parent.parent / "media"
WORDS = {"sugar": "SUGAR", "salt": "SALT", "satfat": "SAT FAT"}


def render(v: Verdict) -> Path:
    MEDIA_DIR.mkdir(exist_ok=True)
    size = 512
    img = Image.new("RGB", (size, size), "white")
    d = ImageDraw.Draw(img)
    c, r = size / 2, size / 2 - 12
    pts = [(c + r * math.cos(math.radians(22.5 + 45 * i)), c + r * math.sin(math.radians(22.5 + 45 * i)))
           for i in range(8)]
    d.polygon(pts, fill="black", outline="white")
    r2 = r - 14
    inner = [(c + r2 * math.cos(math.radians(22.5 + 45 * i)), c + r2 * math.sin(math.radians(22.5 + 45 * i)))
             for i in range(8)]
    d.polygon(inner, outline="white", width=5)

    big, mid, small = (ImageFont.load_default(size=s) for s in (88, 56, 30))
    if v.nutrient == "sugar":
        stat = f"~{v.amount_serving / 4:.1f} tsp"
    else:
        stat = f"~{v.amount_serving:.1f} g"
    for text, font, y in [("HIGH IN", mid, 150), (WORDS[v.nutrient], big, 245),
                          (stat, mid, 340), (f"{round(v.pct_daily)}% of daily limit", small, 405)]:
        d.text((c, y), text, font=font, fill="white", anchor="mm")
    path = MEDIA_DIR / f"{uuid.uuid4().hex}.png"
    img.save(path)
    return path
