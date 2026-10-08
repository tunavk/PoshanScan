# PoshanScan prototype

WhatsApp nutrition nudge: send a barcode photo or a shopping list, get **one warning** and **one affordable swap**.

```
WhatsApp → Twilio → /whatsapp webhook (server.py)
  → bot.py: consent / commands / route input
      ├─ photo with barcode → zxing-cpp decodes → products.py (curated CSV → Open Food Facts)
      ├─ photo without one  → vision.py (Claude) reads list or nutrition table   [optional]
      └─ typed text         → barcode digits, or fuzzy-matched shopping list
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

## 3. Optional: reading list photos and nutrition labels

Put an `ANTHROPIC_API_KEY` in `.env`. Without a key, barcodes and typed lists still work. Photos without a barcode
get a "couldn't read it, type the name instead" reply. With a key, Claude only *transcribes* the photo.
Every health judgement stays in the rule-based `scoring.py`.

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
scan/warning/swap/feedback event. `STOP` deletes all of a user's rows. Nothing is sent to anyone else, except
photos when the optional Claude step is on, and barcodes looked up on Open Food Facts.

To see results: `sqlite3 poshanscan.db "select kind, product, nutrient, detail from events"`.
