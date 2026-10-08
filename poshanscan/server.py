"""WhatsApp webhook via Twilio.

Twilio POSTs each incoming WhatsApp message to /whatsapp. We answer at once (Twilio times out
after 15 s) and send the real replies through Twilio's REST API in the background.
"""
import base64
import hashlib
import hmac
import os
from pathlib import Path

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles

from . import bot
from .label_image import MEDIA_DIR

SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")  # Twilio sandbox number
PUBLIC_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")         # e.g. https://xyz.trycloudflare.com

app = FastAPI(title="PoshanScan")
MEDIA_DIR.mkdir(exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

EMPTY_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'


@app.get("/")
def health():
    return {"ok": True, "service": "PoshanScan", "twilio_configured": bool(SID and TOKEN),
            "public_url": PUBLIC_URL or None}


def _valid_signature(request: Request, params: dict) -> bool:
    """Reject requests that did not come from Twilio (X-Twilio-Signature check)."""
    if not TOKEN or not PUBLIC_URL:
        return True  # local testing
    url = PUBLIC_URL + request.url.path
    payload = url + "".join(k + params[k] for k in sorted(params))
    digest = base64.b64encode(hmac.new(TOKEN.encode(), payload.encode(), hashlib.sha1).digest()).decode()
    return hmac.compare_digest(digest, request.headers.get("X-Twilio-Signature", ""))


@app.post("/whatsapp")
async def whatsapp(request: Request, background: BackgroundTasks):
    form = dict(await request.form())
    if not _valid_signature(request, form):
        raise HTTPException(403, "bad signature")
    background.add_task(_process, form)
    return Response(EMPTY_TWIML, media_type="application/xml")


def _process(form: dict):
    sender = form.get("From", "")
    images = []
    for i in range(int(form.get("NumMedia", "0") or 0)):
        mime = form.get(f"MediaContentType{i}", "")
        if mime.startswith("image/"):
            r = httpx.get(form[f"MediaUrl{i}"], auth=(SID, TOKEN), follow_redirects=True, timeout=20)
            images.append((r.content, mime))
    try:
        replies = bot.handle(bot.Incoming(phone=sender, text=form.get("Body", ""), images=images))
    except Exception as e:  # never leave the user without an answer
        print(f"[bot] error: {e!r}", flush=True)
        replies = [bot.Reply("😕 Sorry, something went wrong. Please try again.")]
    for reply in replies:
        _send(sender, reply)


def _send(to: str, reply: "bot.Reply"):
    if not (SID and TOKEN):
        print(f"[send → {to}] {reply.text}", flush=True)
        return
    data = {"From": FROM, "To": to, "Body": reply.text}
    if reply.image and PUBLIC_URL:
        data["MediaUrl"] = f"{PUBLIC_URL}/media/{Path(reply.image).name}"
    r = httpx.post(f"https://api.twilio.com/2010-04-01/Accounts/{SID}/Messages.json",
                   data=data, auth=(SID, TOKEN), timeout=20)
    if r.status_code >= 300:
        print(f"[twilio] send failed {r.status_code}: {r.text[:300]}", flush=True)
