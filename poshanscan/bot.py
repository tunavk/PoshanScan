"""Conversation logic, independent of WhatsApp. Takes a message in, returns replies out."""
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import zxingcpp
from PIL import Image

from . import label_image, products, store, swaps, vision
from .messages import pattern_line, t, warning, week_summary
from .products import Product
from .scoring import score, Verdict


@dataclass
class Reply:
    text: str
    image: Path | None = None


@dataclass
class Incoming:
    phone: str
    text: str = ""
    images: list[tuple[bytes, str]] = field(default_factory=list)  # (bytes, mime type)


YES = {"yes", "y", "haan", "ha", "han", "हाँ", "हां", "ok", "okay", "agree"}
GREETINGS = {"hi", "hello", "hey", "start", "namaste", "hii"}


def handle(msg: Incoming) -> list[Reply]:
    u = store.uid(msg.phone)
    user = store.get_user(u)
    lang = user["lang"]
    text = msg.text.strip()
    cmd = text.lower().strip(" .!")

    if cmd in {"stop", "delete", "unsubscribe"}:
        store.delete_user(u)
        return [Reply(t(lang, "stopped"))]
    if cmd in {"hindi", "हिंदी"}:
        store.update_user(u, lang="hi")
        return [Reply(t("hi", "ready" if user["consented"] else "welcome"))]
    if cmd == "english":
        store.update_user(u, lang="en")
        return [Reply(t("en", "ready" if user["consented"] else "welcome"))]

    if not user["consented"]:
        if cmd in YES:
            store.update_user(u, consented=1)
            store.log(u, "consent")
            return [Reply(t(lang, "ready"))]
        if user["new"] or cmd in GREETINGS:
            return [Reply(t(lang, "welcome"))]
        return [Reply(t(lang, "need_consent"))]

    if cmd in YES:
        return [Reply(t(lang, "ready"))]
    if cmd in {"help", "?", "menu"} or cmd in GREETINGS:
        return [Reply(t(lang, "help"))]
    if cmd in {"week", "hafta", "हफ़्ता", "हफ्ता"}:
        return [Reply(week_summary(store.week_summary(u), lang))]

    state = user["state"]
    if cmd in {"1", "2"} and state.get("last"):
        store.log(u, "feedback", state["last"], detail="switch" if cmd == "1" else "keep")
        store.update_user(u, state={})
        return [Reply(t(lang, "thanks_switch" if cmd == "1" else "thanks_keep"))]

    if msg.images:
        image, mime = msg.images[0]
        return _handle_image(u, lang, state, image, mime)

    if re.fullmatch(r"\d{8,14}", text.replace(" ", "")):
        return _handle_barcode(u, lang, text.replace(" ", ""))

    items = [x.strip() for x in re.split(r"[\n,;]+", text) if x.strip()]
    if not items:
        return [Reply(t(lang, "help"))]
    return _handle_list(u, lang, items)


# ---------- images ----------

def _decode_barcode(image: bytes) -> str | None:
    try:
        img = Image.open(io.BytesIO(image))
    except Exception:
        return None
    for candidate in (img, img.convert("L")):
        results = zxingcpp.read_barcodes(candidate)
        for r in results:
            if r.text and r.text.isdigit():
                return r.text
    return None


def _handle_image(u, lang, state, image: bytes, mime: str) -> list[Reply]:
    code = _decode_barcode(image)
    if code:
        return _handle_barcode(u, lang, code)

    seen = vision.read_photo(image, mime)
    if not seen:
        return [Reply(t(lang, "no_barcode"))]

    if seen["kind"] == "nutrition_label":
        p = _product_from_label(seen["label"], state.get("pending_barcode", ""))
        if p:
            store.update_user(u, state={})
            return _verdict_replies(u, lang, p, kind="label_scan")
        return [Reply(t(lang, "no_barcode"))]
    if seen["kind"] in ("shopping_list", "product_photo") and seen["items"]:
        return _handle_list(u, lang, seen["items"])
    return [Reply(t(lang, "no_barcode"))]


def _product_from_label(label: dict, barcode: str) -> Product | None:
    if label.get("per") not in ("100g", "100ml"):
        return None
    sodium = label.get("sodium_mg")
    if sodium is None and label.get("salt_g") is not None:
        sodium = label["salt_g"] * 400  # 1 g salt = 400 mg sodium
    if label.get("sugar_g") is None and sodium is None and label.get("satfat_g") is None:
        return None
    return Product(
        name=label.get("product_name") or "This product",
        category="any", form="liquid" if label["per"] == "100ml" else "solid",
        sugar_g=label.get("sugar_g"), sodium_mg=sodium, satfat_g=label.get("satfat_g"),
        kcal=label.get("kcal"), serving=label.get("serving_size"),
        barcode=barcode, source="label photo",
    )


# ---------- barcode / list ----------

def _handle_barcode(u, lang, code: str) -> list[Reply]:
    p = products.by_barcode(code)
    if not p:
        store.log(u, "unknown_barcode", detail=code)
        store.update_user(u, state={"pending_barcode": code})
        return [Reply(t(lang, "barcode_unknown", code=code))]
    return _verdict_replies(u, lang, p, kind="barcode_scan")


MAX_LIST_WARNINGS = 5  # beyond this, extra flagged items are just named, so the chat isn't flooded


def _handle_list(u, lang, items: list[str]) -> list[Reply]:
    found, unknown = [], []
    for it in items:
        p = products.by_name(it)
        (found if p else unknown).append(p or it)
    # de-duplicate (same product written twice)
    found = list({p.name: p for p in found}.values())
    if not found:
        return [Reply(t(lang, "nothing_found"))]

    if len(found) == 1 and len(items) == 1:
        return _verdict_replies(u, lang, found[0], kind="name_lookup")

    verdicts = [score(p) for p in found]
    # Worst first by how far over its "high in" threshold each item is, so salt and fat
    # problems aren't drowned out by sugar's tighter daily limit.
    high = sorted((v for v in verdicts if v.is_high), key=lambda v: v.ratio, reverse=True)
    fine = [v.product.name for v in verdicts if not v.is_high]
    store.log(u, "list", detail=f"{len(found)} found, {len(high)} high, {len(unknown)} unknown")
    for name in fine:
        store.log(u, "list_item", name, detail="ok")

    extras = []
    if fine:
        extras.append(t(lang, "list_fine", items=", ".join(fine)))
    if unknown:
        extras.append(t(lang, "unknown_items", items=", ".join(unknown[:5])))
    if not high:
        return [Reply("\n\n".join([t(lang, "list_all_ok", n=len(found))] + extras))]

    replies = [Reply("\n\n".join([t(lang, "list_head", n=len(found), high=len(high))] + extras))]
    shown, rest = high[:MAX_LIST_WARNINGS], high[MAX_LIST_WARNINGS:]
    for v in shown:
        replies.append(_warning_reply(u, lang, v, kind="list_item", show_pattern=False))
    for v in rest:
        store.log(u, "list_item", v.product.name, v.nutrient)
    if rest:
        replies[-1].text += "\n\n" + t(lang, "list_more", items=", ".join(v.product.name for v in rest))
    replies[-1].text += "\n\n" + t(lang, "list_feedback")
    store.update_user(u, state={"last": ", ".join(v.product.name for v in shown)})
    return replies


def _verdict_replies(u, lang, p: Product, kind: str) -> list[Reply]:
    v = score(p)
    if not v.is_high:
        store.log(u, kind, p.name, detail="ok")
        return [Reply(t(lang, "ok", name=p.name))]
    reply = _warning_reply(u, lang, v, kind)
    reply.text += "\n\n" + t(lang, "feedback")
    store.update_user(u, state={"last": p.name})
    return [reply]


def _warning_reply(u, lang, v: Verdict, kind: str, show_pattern: bool = True) -> Reply:
    """One warning + one swap for one product, logged to the 7-day memory.
    Lists skip the pattern line: counting items within the same list isn't a weekly pattern."""
    swap = swaps.pick(v)
    store.log(u, kind, v.product.name, v.nutrient, swap.text if swap else "")
    body = warning(v, swap, lang)
    repeat = show_pattern and pattern_line(store.high_count_this_week(u, v.nutrient), v.nutrient, lang)
    if repeat:
        body += "\n\n" + repeat
    return Reply(body, image=label_image.render(v))
