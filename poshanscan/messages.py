"""All user-facing text. Tone rule: inform and offer, never shame."""
from .scoring import Verdict
from .swaps import Swap

T = {
    "en": {
        "welcome": (
            "🙏 Namaste! I'm *PoshanScan*.\n\n"
            "Send me a *photo of a barcode* or your *shopping list* and I'll tell you the one thing "
            "to watch and one easy swap.\n\n"
            "🔒 To do this I store your scans (not your name). Your number is stored in scrambled form. "
            "Type *STOP* at any time to delete everything.\n\n"
            "Reply *YES* to agree and start. (हिंदी के लिए *HINDI* लिखें)"
        ),
        "ready": "✅ All set! Send a barcode photo, a photo of your list, or type your list like:\n_maggi, thums up, parle g_",
        "stopped": "🗑️ Done. Your data has been deleted and you won't get messages from me. Send *HI* any time to start again.",
        "help": "📷 Send a *barcode photo* or *shopping list* (photo or typed, e.g. _maggi, pepsi, marie_).\n"
                "*WEEK* for your last 7 days · *HINDI* / *ENGLISH* to switch language · *STOP* to delete your data.",
        "pattern": "📅 That's your *{nth}* item high in {nutrient} this week.",
        "pattern_strong": "📅 That's your *{nth}* item high in {nutrient} this week. Swapping just one of them makes a difference.",
        "week_head": "📅 *Your last 7 days*",
        "week_checked": "• {n} item(s) checked",
        "week_high": "• High in: {parts}",
        "week_swaps": "• You said you'd try {s} of {a} swaps",
        "week_empty": "📅 No items checked in the last 7 days. Send a barcode or list to start!",
        "need_consent": "Please reply *YES* first so I can check your products. 🙂",
        "label": {"sugar": "HIGH IN SUGAR", "salt": "HIGH IN SALT", "satfat": "HIGH IN SATURATED FAT"},
        "sugar_line": "🥄 About *{tsp} teaspoons of sugar* in {serving}",
        "salt_line": "🧂 About *{amt:.1f} g of salt* in {serving}",
        "satfat_line": "🧈 About *{amt:.1f} g of saturated fat* in {serving}",
        "daily": "{bar} *{pct}%* of a whole day's limit (ICMR-NIN)",
        "try": "💡 *Try instead:* {swap}",
        "pct_less": " ({pct}% less {nutrient})",
        "nutrient": {"sugar": "sugar", "salt": "salt", "satfat": "saturated fat"},
        "feedback": "Reply *1* if you'll try the swap, *2* if you'll keep the original.",
        "ok": "✅ *{name}* isn't high in sugar, salt or saturated fat. Good pick! 👍",
        "list_head": "🛒 I checked *{n}* item(s). *{high}* high in sugar, salt or fat, worst first 👇",
        "list_fine": "✅ Look fine: {items}",
        "list_more": "➕ Also high: {items}",
        "list_feedback": "Reply *1* if you'll try at least one of these swaps, *2* if you'll keep your list as it is.",
        "list_all_ok": "🛒 I checked *{n}* item(s). None are high in sugar, salt or saturated fat. 👍",
        "unknown_items": "❓ Didn't recognise: {items}",
        "nothing_found": "😕 I couldn't recognise any products there. Try typing them, e.g. _maggi, pepsi, marie_.",
        "barcode_unknown": "🔍 I don't have barcode *{code}* yet. Send a clear photo of the *nutrition table* on the back of the pack and I'll read it.",
        "no_barcode": "📷 I couldn't read a barcode in that photo. Try again closer and in good light, or just type the product name.",
        "thanks_switch": "🙌 Great choice! Small swaps add up.",
        "thanks_keep": "👍 Thanks for telling me. Every scan still helps you notice.",
        "serving_pack": "one {amt:g} {unit} serving",
        "serving_100": "100 {unit}",
        "source_off": "_(data: Open Food Facts, may vary from your pack)_",
        "source_label": "_(read from your photo of the label)_",
    },
    "hi": {
        "welcome": "🙏 नमस्ते! मैं *PoshanScan* हूँ।\n\nबारकोड या शॉपिंग लिस्ट की फोटो भेजें।",
        "ready": "✅ तैयार! बारकोड की फोटो, लिस्ट की फोटो, या लिस्ट टाइप करें, जैसे:\n_maggi, thums up, parle g_",
        "stopped": "🗑️ आपका डेटा मिटा दिया गया है। फिर से शुरू करने के लिए *HI* भेजें।",
        "help": "📷 *बारकोड* या *शॉपिंग लिस्ट* की फोटो भेजें, या लिस्ट टाइप करें।\n*WEEK* पिछले 7 दिन · *ENGLISH* भाषा बदलने के लिए · *STOP* डेटा मिटाने के लिए।",
        "pattern": "📅 इस हफ़्ते यह आपका *{nth}* ज़्यादा {nutrient} वाला प्रोडक्ट है।",
        "pattern_strong": "📅 इस हफ़्ते यह आपका *{nth}* ज़्यादा {nutrient} वाला प्रोडक्ट है। इनमें से एक भी बदलना फ़र्क लाता है।",
        "week_head": "📅 *आपके पिछले 7 दिन*",
        "week_checked": "• {n} चीज़ें देखीं",
        "week_high": "• ज़्यादा: {parts}",
        "week_swaps": "• आपने {a} में से {s} स्वैप आज़माने को कहा",
        "week_empty": "📅 पिछले 7 दिनों में कुछ नहीं देखा। बारकोड या लिस्ट भेजें!",
        "need_consent": "कृपया पहले *YES* लिखें। 🙂",
        "label": {"sugar": "चीनी ज़्यादा", "salt": "नमक ज़्यादा", "satfat": "सैचुरेटेड फैट ज़्यादा"},
        "sugar_line": "🥄 {serving} में लगभग *{tsp} चम्मच चीनी*",
        "salt_line": "🧂 {serving} में लगभग *{amt:.1f} ग्राम नमक*",
        "satfat_line": "🧈 {serving} में लगभग *{amt:.1f} ग्राम सैचुरेटेड फैट*",
        "daily": "{bar} पूरे दिन की सीमा का *{pct}%* (ICMR-NIN)",
        "try": "💡 *इसकी जगह आज़माएँ:* {swap}",
        "pct_less": " ({pct}% कम {nutrient})",
        "nutrient": {"sugar": "चीनी", "salt": "नमक", "satfat": "सैचुरेटेड फैट"},
        "feedback": "स्वैप करेंगे तो *1* लिखें, वही लेंगे तो *2*।",
        "ok": "✅ *{name}* में चीनी, नमक या सैचुरेटेड फैट ज़्यादा नहीं है। बढ़िया! 👍",
        "list_head": "🛒 मैंने *{n}* चीज़ें देखीं। *{high}* में चीनी, नमक या फैट ज़्यादा है, सबसे ज़्यादा वाली पहले 👇",
        "list_fine": "✅ ठीक हैं: {items}",
        "list_more": "➕ ये भी ज़्यादा हैं: {items}",
        "list_feedback": "कम से कम एक स्वैप आज़माएँगे तो *1* लिखें, लिस्ट वैसी ही रखेंगे तो *2*।",
        "list_all_ok": "🛒 मैंने *{n}* चीज़ें देखीं। किसी में भी चीनी, नमक या फैट ज़्यादा नहीं है। 👍",
        "unknown_items": "❓ पहचान नहीं पाया: {items}",
        "nothing_found": "😕 कोई प्रोडक्ट पहचान नहीं पाया। नाम टाइप करके देखें, जैसे _maggi, pepsi_।",
        "barcode_unknown": "🔍 बारकोड *{code}* मेरे पास नहीं है। पैकेट के पीछे की *न्यूट्रिशन टेबल* की साफ़ फोटो भेजें।",
        "no_barcode": "📷 फोटो में बारकोड नहीं पढ़ पाया। पास से, अच्छी रोशनी में फिर से भेजें, या नाम टाइप करें।",
        "thanks_switch": "🙌 बढ़िया! छोटे बदलाव मिलकर बड़ा फ़र्क लाते हैं।",
        "thanks_keep": "👍 बताने के लिए धन्यवाद।",
        "serving_pack": "एक {amt:g} {unit} सर्विंग",
        "serving_100": "100 {unit}",
        "source_off": "_(डेटा: Open Food Facts)_",
        "source_label": "_(आपकी लेबल फोटो से पढ़ा गया)_",
    },
}
# Hindi users still see the consent/privacy details in full.
T["hi"]["welcome"] += "\n\n" + T["en"]["welcome"].split("\n\n", 1)[1]


def t(lang: str, key: str, **kw) -> str:
    s = T.get(lang, T["en"]).get(key, T["en"][key])
    return s.format(**kw) if kw else s


def _bar(pct: float) -> str:
    filled = min(10, max(1, round(pct / 10)))
    return "⬛" * filled + "⬜" * (10 - filled)  # not red: Indian shoppers read red as the non-veg mark


def _fmt_tsp(grams: float) -> str:
    tsp = grams / 4  # 1 teaspoon of sugar ≈ 4 g
    return f"{tsp:.1f}".rstrip("0").rstrip(".") if tsp < 1 else str(round(tsp * 2) / 2).removesuffix(".0")


def warning(v: Verdict, swap: Swap | None, lang: str) -> str:
    p = v.product
    L = T.get(lang, T["en"])
    serving = (t(lang, "serving_pack", amt=p.serving, unit=p.unit) if p.serving
               else t(lang, "serving_100", unit=p.unit))
    if v.nutrient == "sugar":
        amount_line = t(lang, "sugar_line", tsp=_fmt_tsp(v.amount_serving), serving=serving)
    else:
        amount_line = t(lang, f"{v.nutrient}_line", amt=v.amount_serving, serving=serving)
    lines = [
        f"⚠️ *{L['label'][v.nutrient]}*",
        f"*{p.name}*",
        amount_line,
        t(lang, "daily", bar=_bar(v.pct_daily), pct=round(v.pct_daily)),
    ]
    if swap:
        s = swap.text
        if swap.pct_less:
            s += t(lang, "pct_less", pct=swap.pct_less, nutrient=L["nutrient"][v.nutrient])
        if swap.cost_note:
            s += f", {swap.cost_note}"
        lines += ["", t(lang, "try", swap=s)]
    if p.source == "Open Food Facts":
        lines += ["", t(lang, "source_off")]
    elif p.source == "label photo":
        lines += ["", t(lang, "source_label")]
    return "\n".join(lines)


HINDI_ORDINALS = {2: "दूसरा", 3: "तीसरा", 4: "चौथा", 5: "पाँचवाँ", 6: "छठा"}


def _ordinal(n: int, lang: str) -> str:
    if lang == "hi":
        return HINDI_ORDINALS.get(n, f"{n}वाँ")
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def pattern_line(count: int, nutrient: str, lang: str) -> str:
    """Nudge only once there's a pattern: the 2nd+ item high in the same thing within 7 days."""
    if count < 2:
        return ""
    key = "pattern_strong" if count >= 3 else "pattern"
    return t(lang, key, nth=_ordinal(count, lang), nutrient=T.get(lang, T["en"])["nutrient"][nutrient])


def week_summary(w: dict, lang: str) -> str:
    if not w["checked"]:
        return t(lang, "week_empty")
    names = T.get(lang, T["en"])["nutrient"]
    lines = [t(lang, "week_head"), t(lang, "week_checked", n=w["checked"])]
    if w["high"]:
        parts = " · ".join(f"{names[k]} {n}" for k, n in sorted(w["high"].items(), key=lambda x: -x[1]))
        lines.append(t(lang, "week_high", parts=parts))
    if w["answered"]:
        lines.append(t(lang, "week_swaps", s=w["switch"], a=w["answered"]))
    return "\n".join(lines)
