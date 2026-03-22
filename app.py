import os
import logging
import requests
import threading
from flask import Flask, request

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

# ================= TELEGRAM =================

def send_message(chat_id, text):
    if not BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

# ================= WEBHOOK =================

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json()

        if not data:
            return "ok", 200

        logging.info(data)

        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")

            if text == "/start":
                send_message(chat_id, "✅ البوت يعمل 100%")
            else:
                send_message(chat_id, f"📩 وصلت رسالتك: {text}")

        return "ok", 200

    except Exception as e:
        logging.error(e)
        return "ok", 200


@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

# ================= RUN =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
