"""Conversation logic, independent of WhatsApp. Takes a message in, returns replies out."""
import io
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import zxingcpp
from PIL import Image

from . import contrib, label_image, products, quality, store, swaps, vision
from .messages import choose_list, pattern_line, t, warning, week_summary
from .model import match_score, tokens
from .products import Product
from .scoring import score, Verdict

FLOW_TIMEOUT = 10 * 60      # "teach me this product" / "which one is it?" expire after 10 minutes
MATCH_SURE = 0.8            # front-of-pack match score needed to answer without asking
MATCH_MARGIN = 0.15         # ...and how far ahead of the runner-up it must be
MATCH_MAYBE = 0.5           # below this a candidate isn't worth offering


@dataclass
class Reply:
    text: str
    image: Path | None = None


@dataclass
class Incoming:
    phone: str
    text: str = ""
    images: list[tuple[bytes, str]] = field(default_factory=list)  # (bytes, mime type)


def intro(lang: str, key: str) -> str:
    """Welcome / ready / help text. Without photo reading, the barcode-only version, so the bot
    never invites photos of fronts, labels or lists that it can't read."""
    return t(lang, key if vision.available() else f"{key}_barcode")


YES = {"yes", "y", "haan", "ha", "han", "हाँ", "हां", "ok", "okay", "agree"}
GREETINGS = {"hi", "hello", "hey", "start", "namaste", "hii"}


def handle(msg: Incoming) -> list[Reply]:
    u = store.uid(msg.phone)
    user = store.get_user(u)
    lang = user["lang"]
    text = msg.text.strip()
    cmd = text.lower().strip(" .!")

    if cmd in {"stop", "delete", "unsubscribe"}:
        contrib.anonymise(u)
        store.delete_user(u)
        return [Reply(t(lang, "stopped"))]
    if cmd in {"hindi", "हिंदी"}:
        store.update_user(u, lang="hi")
        return [Reply(intro("hi", "ready" if user["consented"] else "welcome"))]
    if cmd == "english":
        store.update_user(u, lang="en")
        return [Reply(intro("en", "ready" if user["consented"] else "welcome"))]

    if not user["consented"]:
        if cmd in YES:
            store.update_user(u, consented=1)
            store.log(u, "consent")
            return [Reply(intro(lang, "ready"))]
        if user["new"] or cmd in GREETINGS:
            return [Reply(intro(lang, "welcome"))]
        return [Reply(t(lang, "need_consent"))]

    if cmd in YES:
        return [Reply(intro(lang, "ready"))]
    if cmd in {"help", "?", "menu"} or cmd in GREETINGS:
        return [Reply(intro(lang, "help"))]
    if cmd in {"week", "hafta", "हफ़्ता", "हफ्ता"}:
        return [Reply(week_summary(store.week_summary(u), lang))]

    state = user["state"]
    for flow in ("teach", "choose"):
        if state.get(flow) and state[flow].get("expires", 0) < time.time():
            state.pop(flow)
    if cmd in {"skip", "cancel"} and (state.get("teach") or state.get("choose")):
        state.pop("teach", None), state.pop("choose", None)
        store.update_user(u, state=state)
        return [Reply(t(lang, "skipped"))]
    if state.get("choose") and cmd.isdigit():
        return _handle_choice(u, lang, state, int(cmd))
    if cmd in {"1", "2"} and state.get("last"):
        store.log(u, "feedback", state["last"], detail="switch" if cmd == "1" else "keep")
        store.update_user(u, state={})
        return [Reply(t(lang, "thanks_switch" if cmd == "1" else "thanks_keep"))]

    if msg.images:
        return _handle_images(u, lang, state, msg.images)

    if re.fullmatch(r"\d{8,14}", text.replace(" ", "")):
        return _handle_barcode(u, lang, text.replace(" ", ""))

    items = [x.strip() for x in re.split(r"[\n,;]+", text) if x.strip()]
    if not items:
        return [Reply(intro(lang, "help"))]
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


def _handle_images(u, lang, state, images: list[tuple[bytes, str]]) -> list[Reply]:
    """Read every photo in the message (a shopper may send barcode + front + label together),
    merge with any "teach me this product" flow in progress, then decide what to answer."""
    teach = state.get("teach") or {}
    new_code, front, label, listed, label_unreadable = "", teach.get("front"), None, [], False
    for image, mime in images[:4]:
        code = _decode_barcode(image)
        if code:
            if code != teach.get("barcode"):  # a different product: drop the flow in progress
                teach, front = {}, None
            new_code = code
            continue
        seen = vision.read_photo(image, mime)
        if not seen:
            continue
        if seen["kind"] == "nutrition_label":
            if seen["label"]["per"] in ("100g", "100ml"):
                label = seen["label"]
            else:
                label_unreadable = True
        elif seen["kind"] == "product_photo" and (seen["product"]["brand"] or seen["product"]["name"]):
            front = seen["product"]
        elif seen["kind"] == "shopping_list" and seen["items"]:
            listed = seen["items"]

    if label:
        return _from_label(u, lang, state, teach, label, new_code or teach.get("barcode", ""), front)
    if label_unreadable:
        return [Reply(t(lang, "label_unreadable"))]
    if new_code:
        return _handle_barcode(u, lang, new_code, front=front)
    if front:
        return _from_front(u, lang, state, teach, front)
    if listed:
        return _handle_list(u, lang, listed)
    return [Reply(t(lang, "photo_unreadable" if vision.available() else "no_barcode"))]


def _front_name(front: dict | None) -> str:
    if not front:
        return ""
    return " ".join(x for x in (front["brand"], front["name"], front["variant"]) if x).strip()


def _save_flow(u, state, flow: str, data: dict) -> None:
    state.pop("teach", None), state.pop("choose", None)
    if data:
        state[flow] = {**data, "expires": time.time() + FLOW_TIMEOUT}
    store.update_user(u, state=state)


def _from_label(u, lang, state, teach, label: dict, barcode: str, front: dict | None) -> list[Reply]:
    """A nutrition table was read: answer from it, and remember the product for everyone else."""
    sodium = label["sodium_mg"]
    if sodium is None and label["salt_g"] is not None:
        sodium = label["salt_g"] * 400  # 1 g salt = 400 mg sodium
    if quality.problems(label["sugar_g"], sodium, label["satfat_g"], label["kcal"],
                        label["fat_g"], label["carbs_g"], label["protein_g"]):
        return [Reply(t(lang, "label_unreadable"))]
    known = products.by_barcode(barcode) if barcode else None
    name = _front_name(front) or label["product_name"] or (known.name if known else "")
    category = (front or {}).get("category") or (known.category if known else "any")
    p = Product(
        name=name or t(lang, "this_product"), category=category,
        form="liquid" if label["per"] == "100ml" else "solid",
        sugar_g=label["sugar_g"], sodium_mg=sodium, satfat_g=label["satfat_g"], kcal=label["kcal"],
        serving=label["serving_size"], pack=(front or {}).get("pack_size"),
        barcode=barcode, source="label photo",
    )
    saved_key = None
    if (barcode or name) and not (known and known.source in ("curated", "imported")):
        saved = Product(**{**p.__dict__, "name": name})
        saved_key = contrib.save(u, saved)
        store.log(u, "contribution", name or barcode, detail=saved_key)

    replies = _verdict_replies(u, lang, p, kind="label_scan")
    if saved_key and not name:
        replies[-1].text += "\n\n" + t(lang, "saved") + "\n" + t(lang, "need_front")
        _save_flow(u, store.get_user(u)["state"], "teach", {"barcode": barcode, "key": saved_key})
    else:
        if saved_key:
            replies[-1].text += "\n\n" + t(lang, "saved")
        _save_flow(u, store.get_user(u)["state"], "teach", {})
    return replies


def _from_front(u, lang, state, teach, front: dict) -> list[Reply]:
    """A photo of the front of a pack: find which product it is."""
    name = _front_name(front)
    if teach.get("key"):  # label already saved, this photo names it
        contrib.rename(teach["key"], u, name, front["category"])
        _save_flow(u, state, "teach", {})
        return [Reply(t(lang, "named", name=name))]
    if teach.get("barcode"):  # unknown barcode: front first, label still to come
        _save_flow(u, state, "teach", {"barcode": teach["barcode"], "front": front})
        return [Reply(t(lang, "got_front", name=name))]

    brand = tokens(front["brand"])
    # Another brand's product is a different product, whatever the name says.
    hits = [(p, s) for p, s in products.search(name, limit=6)
            if s >= MATCH_MAYBE and (not brand or match_score(brand, tokens(" ".join([p.name] + p.aliases))) >= 0.75)][:3]
    must_ask = False
    if brand and not front["variant"]:
        # Flavour not visible: if we know several products of this brand, ask rather than guess
        # (Lay's Classic and Lay's Cream & Onion differ a lot in salt).
        same_brand = [(p, s) for p, s in products.search(front["brand"] + " " + name, limit=6)
                      if brand <= tokens(" ".join([p.name] + p.aliases))]
        if len(same_brand) > 1:
            hits, must_ask = same_brand[:3], True
    store.log(u, "front_photo", name, detail=f"{len(hits)} candidates, top {hits[0][1]:.2f}" if hits else "no match")
    close = [p for p, s in hits if hits and s >= hits[0][1] - MATCH_MARGIN]
    # Several close matches are usually the same product entered more than once; asking only
    # helps if they'd get different warnings.
    same_answer = len({score(p).nutrient for p in close}) == 1
    if hits and hits[0][1] >= MATCH_SURE and not must_ask and (len(close) == 1 or same_answer):
        replies = _verdict_replies(u, lang, hits[0][0], kind="front_scan")
        replies[-1].text += "\n\n" + t(lang, "matched_hint")
        return replies
    if hits:
        _save_flow(u, state, "choose", {"options": [{"barcode": p.barcode, "name": p.name} for p, _ in hits],
                                        "front": front})
        return [Reply(choose_list([p.name for p, _ in hits], lang))]
    _save_flow(u, state, "teach", {"barcode": "", "front": front})
    return [Reply(t(lang, "unknown_front", name=name))]


def _handle_choice(u, lang, state, n: int) -> list[Reply]:
    """Answer to "Which one is it?"."""
    choose = state["choose"]
    if n == 0 or n > len(choose["options"]):
        _save_flow(u, state, "teach", {"barcode": "", "front": choose["front"]})
        return [Reply(t(lang, "unknown_front", name=_front_name(choose["front"])))]
    picked = choose["options"][n - 1]
    p = (products.by_barcode(picked["barcode"]) if picked["barcode"]
         else contrib.product_for(contrib.key_for("", picked["name"])))
    _save_flow(u, state, "choose", {})
    if not p:
        return [Reply(t(lang, "photo_unreadable"))]
    return _verdict_replies(u, lang, p, kind="front_scan")


# ---------- barcode / list ----------

def _handle_barcode(u, lang, code: str, front: dict | None = None) -> list[Reply]:
    p = products.by_barcode(code)
    if p:
        _save_flow(u, store.get_user(u)["state"], "teach", {})
        return _verdict_replies(u, lang, p, kind="barcode_scan")
    store.log(u, "unknown_barcode", detail=code)
    _save_flow(u, store.get_user(u)["state"], "teach", {"barcode": code, "front": front})
    if not vision.available():
        return [Reply(t(lang, "barcode_unknown_novision", code=code))]
    if front:
        return [Reply(t(lang, "got_front", name=_front_name(front)))]
    return [Reply(t(lang, "teach_ask", code=code))]


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
