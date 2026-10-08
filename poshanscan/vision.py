"""Read photos that have no barcode: shopping lists and nutrition tables (Claude vision).

Optional: needs ANTHROPIC_API_KEY. Without it, the bot still handles barcodes and typed lists.
The model only *transcribes*; all health judgements stay in scoring.py.
"""
import base64
import json
import os

import anthropic

MODEL = "claude-opus-5-5"

SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["shopping_list", "nutrition_label", "product_photo", "other"]},
        "items": {"type": "array", "items": {"type": "string"},
                  "description": "shopping_list: each item as written (brand/product name, no quantities). "
                                 "product_photo: the single product's brand and name."},
        "label": {
            "type": "object",
            "properties": {
                "product_name": {"type": "string"},
                "per": {"type": "string", "enum": ["100g", "100ml", "unknown"]},
                "sugar_g": {"type": ["number", "null"]},
                "sodium_mg": {"type": ["number", "null"]},
                "salt_g": {"type": ["number", "null"]},
                "satfat_g": {"type": ["number", "null"]},
                "kcal": {"type": ["number", "null"]},
                "serving_size": {"type": ["number", "null"]},
            },
            "required": ["product_name", "per", "sugar_g", "sodium_mg", "salt_g", "satfat_g", "kcal", "serving_size"],
            "additionalProperties": False,
        },
    },
    "required": ["kind", "items", "label"],
    "additionalProperties": False,
}

PROMPT = """This photo was sent to an Indian grocery nutrition assistant. Classify it and transcribe it.
- shopping_list: a handwritten or typed list (any language/script; write items in English letters, e.g. "मैगी" -> "maggi").
- nutrition_label: a nutrition information table. Copy the per-100g or per-100ml column values exactly.
  If only per-serving values exist, set per to "unknown". Use null for anything not printed.
- product_photo: the front of a single packaged product; put its brand and name in items.
- other: anything else.
Fill unused fields with empty values (empty list, empty string, "unknown", nulls). Do not guess numbers."""


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
