"""Read photos that have no barcode: product fronts, nutrition tables and shopping lists (Claude vision).

Needs ANTHROPIC_API_KEY. Without it, the bot still handles barcodes and typed lists.
The model only *transcribes*; all health judgements stay in scoring.py.
"""
import base64
import json
import os

import anthropic

MODEL = "claude-opus-5-5"

CATEGORIES = ["biscuit", "chips", "noodles", "soft_drink", "juice_drink", "energy_drink", "malt_drink",
              "chocolate", "spread", "cereal", "condiment", "dairy_drink", "fat", "bread", "breakfast",
              "healthy_snack", "any"]
_num = {"type": ["number", "null"]}

SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["shopping_list", "nutrition_label", "product_photo", "other"]},
        "items": {"type": "array", "items": {"type": "string"},
                  "description": "shopping_list only: each item as written (brand/product name, no quantities)."},
        "product": {
            "type": "object",
            "description": "product_photo: what is printed on the front of the pack.",
            "properties": {
                "brand": {"type": "string"},
                "name": {"type": "string"},
                "variant": {"type": "string", "description": "flavour or variant, e.g. 'Cream & Onion', 'Atta'"},
                "pack_size": _num,
                "category": {"type": "string", "enum": CATEGORIES},
                "is_liquid": {"type": "boolean"},
            },
            "required": ["brand", "name", "variant", "pack_size", "category", "is_liquid"],
            "additionalProperties": False,
        },
        "label": {
            "type": "object",
            "properties": {
                "product_name": {"type": "string"},
                "per": {"type": "string", "enum": ["100g", "100ml", "unknown"]},
                "sugar_g": _num, "sodium_mg": _num, "salt_g": _num, "satfat_g": _num,
                "fat_g": _num, "carbs_g": _num, "protein_g": _num, "kcal": _num,
                "serving_size": _num,
            },
            "required": ["product_name", "per", "sugar_g", "sodium_mg", "salt_g", "satfat_g",
                         "fat_g", "carbs_g", "protein_g", "kcal", "serving_size"],
            "additionalProperties": False,
        },
    },
    "required": ["kind", "items", "product", "label"],
    "additionalProperties": False,
}

PROMPT = """This photo was sent to an Indian grocery nutrition assistant. Classify it and transcribe it.
- shopping_list: a handwritten or typed list (any language/script; write items in English letters, e.g. "मैगी" -> "maggi").
- nutrition_label: a nutrition information table. Copy the per-100g or per-100ml column values exactly.
  If only per-serving values exist, set per to "unknown". Use null for anything not printed.
  sugar_g is total sugars. pack/serving sizes are in g or ml.
- product_photo: the front of one packaged product. Copy the brand, product name and flavour/variant
  exactly as printed (in English letters), the pack size in g or ml if printed, and pick the closest category.
- other: anything else.
Fill unused fields with empty values (empty list, empty strings, "any", false, "unknown", nulls).
Do not guess numbers or names that are not printed."""


def available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


_client = None


def read_photo(image: bytes, media_type: str) -> dict | None:
    global _client
    if not available():
        return None
    if media_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        media_type = "image/jpeg"
    _client = _client or anthropic.Anthropic()
    try:
        response = _client.beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                             "data": base64.standard_b64encode(image).decode()}},
                {"type": "text", "text": PROMPT},
            ]}],
        )
    except anthropic.APIStatusError as e:
        print(f"[vision] API error {e.status_code}: {e.message}")
        return None
    except anthropic.APIConnectionError as e:
        print(f"[vision] connection error: {e}")
        return None
    if response.stop_reason == "refusal":
        return None
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
