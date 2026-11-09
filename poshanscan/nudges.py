"""Daily reminders from the team's "Nudge Messages" sheet (data/team/nudges.json).

Which message wins when several apply (the team's order):
  1. streak: 3+ days in a row with a sugary / salty / fried pick (first such pick of the day)
  2. high sugar: running teaspoons for the day       (2nd+ high-sugar pick; the 1st is already in the warning)
  3. high salt: running grams of salt for the day     (2nd+ salty pick)
  4. fried, with no sugar or salt warning
  5. clean pick: praise
English text is the team's (edit it in the spreadsheet); Hindi is built in below.
"""
from . import store, team
from .scoring import DAILY_LIMIT, TSP_G, Verdict, per_serving

ORDINALS = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"]
HINDI_ORDINALS = ["पहली", "दूसरी", "तीसरी", "चौथी", "पाँचवीं", "छठी", "सातवीं", "आठवीं", "नौवीं", "दसवीं"]  # feminine: "चीज़"
DAY_WORDS = {1: "a day's", 2: "two days'", 3: "three days'", 4: "four days'"}

HINDI = {
    "sugar_n": "आज यह आपकी {ordinal} ज़्यादा चीनी वाली चीज़ है। आप {limit_tsp} में से {tsp_today} चम्मच पर हैं। "
               "{swap_name} भी वैसा ही स्वाद देगा।",
    "sugar_over": "आज यह आपकी {ordinal} ज़्यादा चीनी वाली चीज़ है। आप {limit_tsp} में से {tsp_today} चम्मच पर हैं, "
                  "यानी {days_worth} से भी ज़्यादा। {swap_name} भी वैसा ही स्वाद देगा।",
    "salt_n": "आज यह आपकी {ordinal} नमकीन चीज़ है, दिन के {limit_salt} ग्राम में से लगभग {salt_today} ग्राम।",
    "fat": "यह तली हुई चीज़ है। {swap_name} में भी वैसा ही कुरकुरापन है।",
    "streak": "लगातार {days} दिन से {group} चीज़ें। क्या आप तीन ऐसे स्वैप देखना चाहेंगे जो उतने ही {taste} हों?",
    "praise_1": "बढ़िया चुनाव, इसमें कुछ भी ज़्यादा नहीं है।",
    "praise_n": "बढ़िया चुनाव। आज की {count} साफ़-सुथरी चीज़ें।",
    "no_data": "इसका पूरा लेबल अभी हमारे पास नहीं है, इसलिए इस बार कोई रिमाइंडर नहीं।",
}
HINDI_GROUPS = {"sugary": ("मीठी", "मीठे"), "salty": ("नमकीन", "नमकीन"), "fried or fatty": ("तली", "कुरकुरे")}
HINDI_DAYS = {1: "एक दिन", 2: "दो दिन", 3: "तीन दिन", 4: "चार दिन"}

_TEAM = team.nudges()


def _template(key: str, lang: str) -> str:
    if lang == "hi" and key in HINDI:
        return HINDI[key]
    return _TEAM["templates"].get(key, "")


def _ordinal(n: int, lang: str) -> str:
    words = HINDI_ORDINALS if lang == "hi" else ORDINALS
    if n <= len(words):
        return words[n - 1]
    return f"{n}वीं" if lang == "hi" else f"{n}th"


def _num(x: float) -> str:
    """Whole numbers, like the team's examples ("26 of 6 teaspoons"); one decimal below 1."""
    return f"{x:.1f}".rstrip("0").rstrip(".") if x < 1 else f"{round(x)}"


def group_of(v: Verdict) -> str:
    if "sugar" in v.highs:
        return "sugary"
    if "salt" in v.highs:
        return "salty"
    if v.product.fried or "satfat" in v.highs:
        return "fried or fatty"
    return "clean" if not v.no_data else "no data"


def record_and_nudge(u: str, v: Verdict, lang: str, swap_name: str = "") -> str:
    """Log a single product check as today's pick, then return the one reminder that applies ("" if none)."""
    if v.no_data:
        return _template("no_data", lang)
    grp = group_of(v)
    first_of_group_today = grp != "clean" and store.group_today(u, grp) == 0
    sugar = per_serving(v.product, "sugar") or 0
    salt = per_serving(v.product, "salt") or 0
    store.log_intake(u, v.product.name, grp, "sugar" in v.highs, "salt" in v.highs,
                     sugar / TSP_G, salt, not v.is_high and not v.product.fried)
    day = store.today(u)
    limit_tsp = DAILY_LIMIT["sugar"] / TSP_G
    fill = {
        "swap_name": swap_name or ("एक हेल्दी स्वैप" if lang == "hi" else "A healthier swap"),
        "limit_tsp": _num(limit_tsp), "tsp_today": _num(day["sugar_tsp"]),
        "limit_salt": _num(DAILY_LIMIT["salt"]), "salt_today": _num(day["salt_g"]),
    }

    if grp in ("sugary", "salty", "fried or fatty") and first_of_group_today:
        days = store.group_streak(u, grp)
        if days >= 3:
            if lang == "hi":
                word, taste = HINDI_GROUPS[grp]
            else:
                g = _TEAM["groups"].get(grp, {"word": grp, "taste": ""})
                word, taste = g["word"], g["taste"]
            return _template("streak", lang).format(days=days, group=word, taste=taste)
    if "sugar" in v.highs and day["high_sugar"] >= 2:
        over = day["sugar_tsp"] > limit_tsp
        k = max(1, int(day["sugar_tsp"] // limit_tsp))
        days_worth = (HINDI_DAYS if lang == "hi" else DAY_WORDS).get(k, f"{k} days'")
        key = "sugar_over" if over else "sugar_n"
        return _template(key, lang).format(ordinal=_ordinal(day["high_sugar"], lang), days_worth=days_worth, **fill)
    if "salt" in v.highs and day["high_salt"] >= 2:
        return _template("salt_n", lang).format(ordinal=_ordinal(day["high_salt"], lang), **fill)
    if v.product.fried and not ({"sugar", "salt"} & set(v.highs)):
        return _template("fat", lang).format(**fill)
    if grp == "clean":
        n = day["clean"]
        return _template("praise_1" if n <= 1 else "praise_n", lang).format(count=n)
    return ""
