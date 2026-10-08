"""Chat with PoshanScan in the terminal, no WhatsApp needed.

  python simulate.py                 interactive
  python simulate.py "maggi, pepsi"  one message
Inside the chat, send a photo with:  /img path/to/photo.jpg
"""
import mimetypes
import sys

from poshanscan import bot

PHONE = "whatsapp:+910000000000"


def send(text: str):
    images = []
    if text.startswith("/img "):
        path = text[5:].strip().strip("'\"")
        images = [(open(path, "rb").read(), mimetypes.guess_type(path)[0] or "image/jpeg")]
        text = ""
    for r in bot.handle(bot.Incoming(phone=PHONE, text=text, images=images)):
        print("\n🤖 " + r.text.replace("\n", "\n   "))
        if r.image:
            print(f"   [image: {r.image}]")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for m in sys.argv[1:]:
            print(f"👤 {m}")
            send(m)
    else:
        while True:
            try:
                send(input("👤 "))
            except (EOFError, KeyboardInterrupt):
                break
