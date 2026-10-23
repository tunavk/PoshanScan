# PoshanScan prototype

WhatsApp nutrition nudge: send a photo of a product (front or barcode) or a shopping list, get **one warning**
and **one affordable swap**.

```
WhatsApp → Twilio → /whatsapp webhook (server.py)
  → bot.py: consent / commands / route input (all photos in a message are read together)
      ├─ barcode            → zxing-cpp decodes → products.py lookup
      ├─ front of pack      → vision.py (Claude) reads brand/name/flavour → products.search → "Which one is it?" if unsure
      ├─ nutrition table    → vision.py reads the numbers → answer straight away + remember the product (contrib.py)
      ├─ list photo         → vision.py reads the items
      └─ typed text         → barcode digits, or fuzzy-matched shopping list
  → products.py lookup order: curated CSV → catalog.db (Open Food Facts India) → shoppers' contributions → live Open Food Facts
     (every source except our own CSV goes through quality.py sanity checks)
  → scoring.py: Chile "high in" thresholds + ICMR-NIN daily limits → single worst nutrient
  → swaps.py: curated swap that is ≥25% lower, adds no new "high in", and costs no more per serving
  → messages.py (English/Hindi) + label_image.py (black octagon PNG)
  → 7-day memory: "That's your 3rd item high in sugar this week" (store.py)
  → reply sent via Twilio REST API; event logged to SQLite (hashed numbers)
```

## 1. Try it locally (no WhatsApp needed)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python simulate.py
```
Type `yes`, then things like `maggi`, `pepsi, parle g, roasted chana`, `8901058000290`,
or `/img path/to/barcode.jpg`. `week` (last 7 days), `hindi`, `english`, `stop` also work.

## 2. Connect to real WhatsApp (Twilio sandbox, ~15 min)

1. Create a free account at twilio.com. In the console, open **Messaging → Try it out → Send a WhatsApp message**.
   From your phone, send the `join <code>` message it shows to **+1 415 523 8886**.
2. Start a public tunnel to your laptop (no account needed):
   ```bash
   brew install cloudflared
   cloudflared tunnel --url http://localhost:8000
   ```
   Copy the `https://….trycloudflare.com` URL it prints.
3. `cp .env.example .env` and fill in `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `PUBLIC_BASE_URL` (the tunnel URL)
   and a random `POSHAN_SALT`.
4. Run the server in a second terminal: `./run.sh`
5. In Twilio's **Sandbox settings**, set *When a message comes in* to `https://….trycloudflare.com/whatsapp` (POST). Save.
6. Message the sandbox number on WhatsApp: `hi`.

The quick-tunnel URL changes each time cloudflared restarts. When it does, update `.env` and the Twilio setting.
Each tester has to send the `join` message once.

## 3. Photos of products, labels and lists

Put an `ANTHROPIC_API_KEY` in `.env`. Without a key, barcodes and typed lists still work, but front-of-pack photos,
nutrition tables, list photos and teaching new products don't. Claude only *reads* the photo (names and printed
numbers). It never estimates nutrients, and every health judgement stays in the rule-based `scoring.py`.

**Teaching the bot a product it doesn't know.** An unknown barcode or front photo makes the bot ask for the nutrition
table (and the front, for the name). The shopper gets their answer from their own photo straight away, and the numbers
are saved for everyone:

- one shopper's reading is shown to others as *"from one shopper's photo, not yet confirmed"*
- once two different shoppers' readings agree (within 10%), it is shown as *"from shoppers' photos"*
- readings that fail the sanity checks (impossible values, calories not matching fat/carbs/protein) are rejected
- photos are never stored, only the numbers; `STOP` keeps a user's contributions but removes the link to them

Check the photo flows without an API key (canned photo readings): `.venv/bin/python tests/test_photo_flows.py`

## 4. The product catalogue

`poshanscan/data/catalog.db` holds the Open Food Facts products sold in India that passed `quality.py`.
`catalog_report.txt` lists how many were kept and why the rest were rejected (useful for the report). To rebuild it with
newer data:

```bash
.venv/bin/pip install -r scripts/requirements-import.txt
.venv/bin/python scripts/import_off.py
```

## Editing the data (no coding needed)

- `poshanscan/data/products.csv` has 50 common Indian products. Values are per 100 g/ml and come from Open Food Facts,
  which is crowd-sourced, so **check each row against the real pack before any pilot**. To add a product, scan its
  barcode with any phone barcode app and copy the nutrition table. `serving` is how much is usually eaten at once.
  `aliases` lists the names people type, separated by `|`. `price_inr` is the pack's MRP. It's blank for now: fill it
  from real packs, and swaps that cost more per serving are then skipped automatically.
- `poshanscan/data/swaps.csv` maps category + nutrient to one swap, either a product barcode or `text:…`. Rows are tried
  in order. A product swap is skipped unless it is ≥25% lower, doesn't add a new problem, and doesn't cost more per
  serving. For product swaps the price note is calculated from `price_inr`. For `text:` swaps, `cost_note` is shown as written.

## Rules used (cite these in the report)

| | Solid (per 100 g) | Liquid (per 100 ml) | Daily limit (ICMR-NIN 2024) |
|---|---|---|---|
| Sugar | 10 g | 5 g | 25 g added sugar |
| Sodium | 400 mg | 100 mg | 5 g salt |
| Saturated fat | 4 g | 3 g | ~22 g (10% of 2000 kcal) |

The thresholds are from Chile's Ley 20.606 (final phase). Labels give *total* sugar, so naturally sweet foods such as lassi
and juice are judged on total sugar. Note this as a limitation.

## Data collected (for the ethics section)

`poshanscan.db` stores a salted hash of the phone number (never the number itself), consent, language, and each
scan/warning/swap/feedback event, plus the label numbers shoppers contribute. `STOP` deletes all of a user's rows and
unlinks their contributions. Photos are sent to Anthropic's API to be read and are not stored by the bot. Barcodes
not in our data are looked up on Open Food Facts. Contributed label numbers are shown to other users, never who sent them.

To see results: `sqlite3 poshanscan.db "select kind, product, nutrient, detail from events"`.
