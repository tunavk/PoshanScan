"""All user-facing text. Tone rule: inform and offer, never shame."""
from .scoring import TSP_G, Verdict, per_serving
from .swaps import Swap

T = {
    "en": {
        "welcome": (
            "🙏 Namaste! I'm *PoshanScan*.\n\n"
            "Send me a *photo of a product* (front or barcode) or your *shopping list* and I'll tell you "
            "the one thing to watch and one easy swap.\n\n"
            "🔒 To do this I store your scans (not your name). Your number is stored in scrambled form. "
            "Photos are read by an AI service and not kept. If you teach me a new product, its label "
            "numbers are shared with other users, never who sent them. "
            "Type *STOP* at any time to delete everything.\n\n"
            "Reply *YES* to agree and start. (हिंदी के लिए *HINDI* लिखें)"
        ),
        "ready": "✅ All set! Send a photo of a product (front or barcode), a photo of your list, or type your list like:\n_maggi, thums up, parle g_",
        "stopped": "🗑️ Done. Your data has been deleted and you won't get messages from me. Send *HI* any time to start again.",
        "help": "📷 Send a photo of a *product* (front or barcode), its *nutrition table*, or your *shopping list* "
                "(photo or typed, e.g. _maggi, pepsi, marie_).\n"
                "*MORE* for more swaps · *WEEK* for your last 7 days · *HINDI* / *ENGLISH* to switch language · *STOP* to delete your data.",
        "week_head": "📅 *Your last 7 days*",
        "week_checked": "• {n} item(s) checked",
        "week_high": "• High in: {parts}",
        "week_swaps": "• You said you'd try {s} of {a} swaps",
        "week_empty": "📅 No items checked in the last 7 days. Send a barcode or list to start!",
        "need_consent": "Please reply *YES* first so I can check your products. 🙂",
        "label": {"sugar": "HIGH IN SUGAR", "salt": "HIGH IN SALT", "satfat": "HIGH IN SATURATED FAT"},
        "sugar_line": "🥄 About *{tsp} teaspoons of sugar* in {serving}",
        "added_sugar_line": "🥄 About *{tsp} teaspoons of added sugar* in {serving}",
        "salt_line": "🧂 About *{amt:.1f} g of salt* in {serving}",
        "satfat_line": "🧈 About *{amt:.1f} g of saturated fat* in {serving}",
        "daily": "{bar} *{pct}%* of a whole day's limit (ICMR-NIN)",
        "try": "💡 *Try instead:* {swap}",
        "pct_less": " ({pct}% less {nutrient})",
        "nutrient": {"sugar": "sugar", "salt": "salt", "satfat": "saturated fat"},
        "feedback": "Reply *1* if you'll try the swap, *2* if you'll keep the original.",
        "ok": "✅ *{name}* · Grade {grade}\n{praise}",
        "ok_default": "Nothing high in sugar, salt or saturated fat. 👍",
        "ok_partial": "✅ *{name}* · Grade {grade}\nNothing high in what we know, but we don't have its {missing} value yet, "
                      "so check the pack.",
        "no_data_product": "❔ *{name}*\nWe don't have its nutrition label yet, so I can't check it.",
        "more_hint": "Reply *MORE* for a cheaper option and the healthiest one.",
        "more_head": "🔁 *More swaps for {name}*",
        "more_none": "I don't have more swaps for that one. Send another product!",
        "swap_labels": {"Same craving": "💙 Same craving", "Cheaper": "💚 Cheaper", "Best for health": "💜 Best for health"},
        "swap_detail": "{name} ({price}grade {grade}). {reason}",
        "swap_saves": "Saves {parts} a serving.",
        "saves_sugar": "{tsp} tsp sugar",
        "saves_salt": "{g} g salt",
        "moderation": "Best in moderation.",
        "source_estimate": "_(estimated values, check the pack)_",
        "source_old_test": "_(from a lab test, the recipe may have changed since)_",
        "list_head": "🛒 I checked *{n}* item(s). *{high}* high in sugar, salt or fat, worst first 👇",
        "list_fine": "✅ Look fine: {items}",
        "list_nodata": "❔ No label data yet: {items}",
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
        "source_contributed": "_(from one shopper's photo of the label, not yet confirmed)_",
        "source_confirmed": "_(from shoppers' photos of the label)_",
        "teach_ask": "🔍 I don't know this product yet (barcode *{code}*). Help me learn it! Send 2 photos:\n"
                     "📸 1. the *front* of the pack\n📸 2. the *nutrition table* on the back\n"
                     "You'll get your answer straight away, and so will the next person who scans it. (*skip* to cancel)",
        "barcode_unknown_novision": "🔍 I don't know barcode *{code}* yet. Try typing the product name instead.",
        "got_front": "👍 Got it: *{name}*. Now send a photo of the *nutrition table* on the back. (*skip* to cancel)",
        "unknown_front": "🔍 I don't know *{name}* yet. Send a photo of its *nutrition table* and I'll check it, "
                         "and remember it for others. (*skip* to cancel)",
        "need_front": "📸 One more: a photo of the *front* of the pack, so others can find it by name. (*skip* to finish)",
        "saved": "🙏 Thanks! I've saved this product, so the next person who scans it gets an answer too.",
        "named": "🙏 Thanks! Saved as *{name}*.",
        "label_unreadable": "📷 I couldn't read the nutrition table clearly. Please send a sharper photo, straight on, "
                            "showing the *per 100 g* (or per 100 ml) column.",
        "photo_unreadable": "📷 I couldn't make out that photo. Try a clear photo of the *front* of the pack, "
                            "its *barcode*, or its *nutrition table*.",
        "choose_head": "🤔 Which one is it?",
        "choose_none": "*0* None of these",
        "matched_hint": "_Not the right product? Send a photo of its barcode._",
        "skipped": "👍 No problem, cancelled.",
        "this_product": "This product",
    },
    "hi": {
        "welcome": "🙏 नमस्ते! मैं *PoshanScan* हूँ।\n\nबारकोड या शॉपिंग लिस्ट की फोटो भेजें।",
        "ready": "✅ तैयार! बारकोड की फोटो, लिस्ट की फोटो, या लिस्ट टाइप करें, जैसे:\n_maggi, thums up, parle g_",
        "stopped": "🗑️ आपका डेटा मिटा दिया गया है। फिर से शुरू करने के लिए *HI* भेजें।",
        "help": "📷 *बारकोड* या *शॉपिंग लिस्ट* की फोटो भेजें, या लिस्ट टाइप करें।\n*MORE* और स्वैप · *WEEK* पिछले 7 दिन · *ENGLISH* भाषा बदलने के लिए · *STOP* डेटा मिटाने के लिए।",
        "week_head": "📅 *आपके पिछले 7 दिन*",
        "week_checked": "• {n} चीज़ें देखीं",
        "week_high": "• ज़्यादा: {parts}",
        "week_swaps": "• आपने {a} में से {s} स्वैप आज़माने को कहा",
        "week_empty": "📅 पिछले 7 दिनों में कुछ नहीं देखा। बारकोड या लिस्ट भेजें!",
        "need_consent": "कृपया पहले *YES* लिखें। 🙂",
        "label": {"sugar": "चीनी ज़्यादा", "salt": "नमक ज़्यादा", "satfat": "सैचुरेटेड फैट ज़्यादा"},
        "sugar_line": "🥄 {serving} में लगभग *{tsp} चम्मच चीनी*",
        "added_sugar_line": "🥄 {serving} में लगभग *{tsp} चम्मच ऊपर से डाली गई चीनी*",
        "salt_line": "🧂 {serving} में लगभग *{amt:.1f} ग्राम नमक*",
        "satfat_line": "🧈 {serving} में लगभग *{amt:.1f} ग्राम सैचुरेटेड फैट*",
        "daily": "{bar} पूरे दिन की सीमा का *{pct}%* (ICMR-NIN)",
        "try": "💡 *इसकी जगह आज़माएँ:* {swap}",
        "pct_less": " ({pct}% कम {nutrient})",
        "nutrient": {"sugar": "चीनी", "salt": "नमक", "satfat": "सैचुरेटेड फैट"},
        "feedback": "स्वैप करेंगे तो *1* लिखें, वही लेंगे तो *2*।",
        "ok": "✅ *{name}* · ग्रेड {grade}\n{praise}",
        "ok_default": "चीनी, नमक या सैचुरेटेड फैट ज़्यादा नहीं है। 👍",
        "ok_partial": "✅ *{name}* · ग्रेड {grade}\nजितना पता है उसमें कुछ ज़्यादा नहीं, पर इसका {missing} हमारे पास नहीं है, "
                      "पैकेट देख लें।",
        "no_data_product": "❔ *{name}*\nइसका न्यूट्रिशन लेबल अभी हमारे पास नहीं है, इसलिए जाँच नहीं कर सकता।",
        "more_hint": "सस्ता और सबसे सेहतमंद विकल्प देखने के लिए *MORE* लिखें।",
        "more_head": "🔁 *{name} के और स्वैप*",
        "more_none": "इसके लिए और स्वैप नहीं हैं। कोई दूसरा प्रोडक्ट भेजें!",
        "swap_labels": {"Same craving": "💙 वही स्वाद", "Cheaper": "💚 सस्ता", "Best for health": "💜 सेहत के लिए सबसे अच्छा"},
        "swap_detail": "{name} ({price}ग्रेड {grade})। {reason}",
        "swap_saves": "हर सर्विंग में {parts} कम।",
        "saves_sugar": "{tsp} चम्मच चीनी",
        "saves_salt": "{g} ग्राम नमक",
        "moderation": "थोड़ी मात्रा में ही लें।",
        "source_estimate": "_(अनुमानित मान, पैकेट देख लें)_",
        "source_old_test": "_(लैब टेस्ट से, रेसिपी बदल चुकी हो सकती है)_",
        "list_head": "🛒 मैंने *{n}* चीज़ें देखीं। *{high}* में चीनी, नमक या फैट ज़्यादा है, सबसे ज़्यादा वाली पहले 👇",
        "list_fine": "✅ ठीक हैं: {items}",
        "list_nodata": "❔ लेबल डेटा अभी नहीं: {items}",
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
        "source_contributed": "_(एक ग्राहक की लेबल फोटो से, अभी पुष्टि नहीं हुई)_",
        "source_confirmed": "_(ग्राहकों की लेबल फोटो से)_",
        "teach_ask": "🔍 यह प्रोडक्ट (बारकोड *{code}*) मेरे पास अभी नहीं है। इसे सीखने में मदद करें! 2 फोटो भेजें:\n"
                     "📸 1. पैकेट का *सामने* का हिस्सा\n📸 2. पीछे की *न्यूट्रिशन टेबल*\n"
                     "आपको जवाब तुरंत मिलेगा, और अगली बार स्कैन करने वाले को भी। (रद्द करने के लिए *skip*)",
        "barcode_unknown_novision": "🔍 बारकोड *{code}* मेरे पास नहीं है। प्रोडक्ट का नाम टाइप करके देखें।",
        "got_front": "👍 मिल गया: *{name}*। अब पीछे की *न्यूट्रिशन टेबल* की फोटो भेजें। (रद्द करने के लिए *skip*)",
        "unknown_front": "🔍 *{name}* मेरे पास अभी नहीं है। इसकी *न्यूट्रिशन टेबल* की फोटो भेजें, मैं जाँच करूँगा "
                         "और दूसरों के लिए याद रखूँगा। (रद्द करने के लिए *skip*)",
        "need_front": "📸 एक और: पैकेट के *सामने* की फोटो, ताकि दूसरे इसे नाम से ढूँढ सकें। (ख़त्म करने के लिए *skip*)",
        "saved": "🙏 धन्यवाद! मैंने यह प्रोडक्ट सेव कर लिया है, अगली बार स्कैन करने वाले को भी जवाब मिलेगा।",
        "named": "🙏 धन्यवाद! *{name}* के नाम से सेव किया।",
        "label_unreadable": "📷 न्यूट्रिशन टेबल साफ़ नहीं पढ़ पाया। सीधी, साफ़ फोटो भेजें जिसमें *प्रति 100 ग्राम* (या 100 ml) वाला कॉलम दिखे।",
        "photo_unreadable": "📷 फोटो समझ नहीं पाया। पैकेट के *सामने*, *बारकोड*, या *न्यूट्रिशन टेबल* की साफ़ फोटो भेजें।",
        "choose_head": "🤔 इनमें से कौन सा है?",
        "choose_none": "*0* इनमें से कोई नहीं",
        "matched_hint": "_सही प्रोडक्ट नहीं है? इसके बारकोड की फोटो भेजें।_",
        "skipped": "👍 ठीक है, रद्द किया।",
        "this_product": "यह प्रोडक्ट",
    },
}
# Barcode-only versions, used when photo reading is off (no ANTHROPIC_API_KEY): never promise what we can't do.
T["en"].update({
    "welcome_barcode": (
        "🙏 Namaste! I'm *PoshanScan*.\n\n"
        "Send me a *photo of a product's barcode*, or type what you're buying (e.g. _maggi, pepsi, parle g_), "
        "and I'll tell you the one thing to watch and one easy swap.\n\n"
        "🔒 To do this I store your scans (not your name). Your number is stored in scrambled form. "
        "Type *STOP* at any time to delete everything.\n\n"
        "Reply *YES* to agree and start. (हिंदी के लिए *HINDI* लिखें)"
    ),
    "ready_barcode": "✅ All set! Send a photo of a product's *barcode*, or type your list like:\n_maggi, thums up, parle g_",
    "help_barcode": "📷 Send a photo of a product's *barcode*, or type products / your shopping list "
                    "(e.g. _maggi, pepsi, marie_).\n"
                    "*MORE* for more swaps · *WEEK* for your last 7 days · *HINDI* / *ENGLISH* to switch language · "
                    "*STOP* to delete your data.",
})
T["hi"].update({
    "welcome_barcode": "🙏 नमस्ते! मैं *PoshanScan* हूँ।\n\nप्रोडक्ट के *बारकोड* की फोटो भेजें, या जो खरीद रहे हैं उसका नाम लिखें।",
    "ready_barcode": "✅ तैयार! प्रोडक्ट के *बारकोड* की फोटो भेजें, या लिस्ट टाइप करें, जैसे:\n_maggi, thums up, parle g_",
    "help_barcode": "📷 प्रोडक्ट के *बारकोड* की फोटो भेजें, या प्रोडक्ट / शॉपिंग लिस्ट टाइप करें।\n"
                    "*MORE* और स्वैप · *WEEK* पिछले 7 दिन · *ENGLISH* भाषा बदलने के लिए · *STOP* डेटा मिटाने के लिए।",
})
# Hindi users still see the consent/privacy details in full.
T["hi"]["welcome"] += "\n\n" + T["en"]["welcome"].split("\n\n", 1)[1]
T["hi"]["welcome_barcode"] += "\n\n" + T["en"]["welcome_barcode"].split("\n\n", 1)[1]


def t(lang: str, key: str, **kw) -> str:
    s = T.get(lang, T["en"]).get(key, T["en"][key])
    return s.format(**kw) if kw else s


def _bar(pct: float) -> str:
    filled = min(10, max(1, round(pct / 10)))
    return "⬛" * filled + "⬜" * (10 - filled)  # not red: Indian shoppers read red as the non-veg mark


def _fmt_tsp(grams: float) -> str:
    tsp = grams / TSP_G  # 1 teaspoon of sugar ≈ 4 g (team setting)
    return f"{tsp:.1f}".rstrip("0").rstrip(".") if tsp < 1 else str(round(tsp * 2) / 2).removesuffix(".0")


def _amount_line(v: Verdict, nutrient: str, lang: str, serving: str) -> str:
    amount = per_serving(v.product, nutrient)
    if nutrient == "sugar":
        key = "added_sugar_line" if v.sugar_basis == "added" else "sugar_line"
        return t(lang, key, tsp=_fmt_tsp(amount), serving=serving)
    return t(lang, f"{nutrient}_line", amt=amount, serving=serving)


def swap_text(swap: Swap, nutrient: str | None, lang: str) -> str:
    """One swap as a sentence: team swaps carry price, grade, reason and what they save."""
    L = T.get(lang, T["en"])
    if not swap.label:  # curated swap table
        s = swap.text
        if swap.pct_less and nutrient:
            s += t(lang, "pct_less", pct=swap.pct_less, nutrient=L["nutrient"][nutrient])
        if swap.cost_note:
            s += f", {swap.cost_note}"
        return s
    price = f"{swap.cost_note}, " if swap.cost_note else ""
    s = t(lang, "swap_detail", name=swap.text, price=price, grade=swap.grade or "?", reason=swap.reason).strip()
    if swap.in_moderation:
        s += " " + t(lang, "moderation")
    saves = []
    if swap.sugar_saved_tsp:
        saves.append(t(lang, "saves_sugar", tsp=f"{round(swap.sugar_saved_tsp, 1):g}"))  # the team's figure as given
    if swap.salt_saved_g:
        saves.append(t(lang, "saves_salt", g=f"{swap.salt_saved_g:g}"))
    if saves:
        s += " " + t(lang, "swap_saves", parts=" + ".join(saves))
    return s


CAPTIONS = {"imported": "source_off", "label photo": "source_label", "contributed": "source_contributed",
            "confirmed": "source_confirmed"}
TEAM_CAPTIONS = {"openfoodfacts": "source_off", "estimate": "source_estimate", "lab_test": "source_old_test"}


def warning(v: Verdict, swap: Swap | None, lang: str) -> str:
    """Grade + every HIGH label, an amount line per flagged nutrient, the day bar for the worst one, one swap."""
    p = v.product
    L = T.get(lang, T["en"])
    serving = (t(lang, "serving_pack", amt=p.serving, unit=p.unit) if p.serving
               else t(lang, "serving_100", unit=p.unit))
    grade = ("ग्रेड " if lang == "hi" else "Grade ") + v.grade
    lines = [
        f"⚠️ *{grade} · {' · '.join(L['label'][n] for n in v.highs)}*",
        f"*{p.name}*",
        _amount_line(v, v.nutrient, lang, serving),
        t(lang, "daily", bar=_bar(v.pct_daily), pct=round(v.pct_daily)),
    ]
    lines += [_amount_line(v, n, lang, serving) for n in v.highs[1:]]
    if swap:
        lines += ["", t(lang, "try", swap=swap_text(swap, v.nutrient, lang))]
    caption = CAPTIONS.get(p.source) or (TEAM_CAPTIONS.get(p.confidence) if p.source == "team" else None)
    if caption:
        lines += ["", t(lang, caption)]
    return "\n".join(lines)


def more_swaps(name: str, swaps: list[Swap], lang: str) -> str:
    if not swaps:
        return t(lang, "more_none")
    labels = T.get(lang, T["en"])["swap_labels"]
    parts = [t(lang, "more_head", name=name)]
    for s in swaps:
        parts.append(f"*{labels.get(s.label, s.label)}:* {swap_text(s, None, lang)}")
    return "\n\n".join(parts)


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


def choose_list(names: list[str], lang: str) -> str:
    lines = [t(lang, "choose_head")] + [f"*{i}* {n}" for i, n in enumerate(names, 1)] + [t(lang, "choose_none")]
    return "\n".join(lines)
