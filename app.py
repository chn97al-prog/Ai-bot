import os
import uuid
import logging
import requests
from flask import Flask, request

# ================== ENV ==================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ================== LOGGING ==================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ================== APP ==================

app = Flask(__name__)
user_state = {}

# ================== HELPERS ==================

def send_message(chat_id, text):
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN missing")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        logging.error("send_message error: %s", e)

def send_photo(chat_id, photo_url):
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN missing")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        requests.post(url, json={"chat_id": chat_id, "photo": photo_url}, timeout=20)
    except Exception as e:
        logging.error("send_photo error: %s", e)

# ================== OPENAI CHAT ==================

def ask_ai(prompt):
    if not OPENAI_API_KEY:
        return "❌ OPENAI_API_KEY غير مضاف في Railway"

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        res = requests.post(url, headers=headers, json=data, timeout=20)
        if res.status_code != 200:
            return f"❌ خطأ: {res.text}"

        return res.json()["choices"][0]["message"]["content"]

    except Exception as e:
        return f"❌ Exception: {e}"

# ================== IMAGE ==================

def generate_image(prompt):
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY missing")

    url = "https://api.openai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    data = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "size": "1024x1024"
    }

    res = requests.post(url, headers=headers, json=data, timeout=30)

    if res.status_code != 200:
        raise Exception(res.text)

    return res.json()["data"][0]["url"]

# ================== WEBHOOK ==================

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json()

        if not data or "message" not in data:
            return "ok", 200

        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text")
        photo = msg.get("photo")

        state = user_state.get(chat_id, "chat")

        # ===== Commands =====

        if text == "/start":
            user_state[chat_id] = "chat"
            send_message(chat_id, "👋 أهلاً بك")
            return "ok", 200

        elif text == "/chat":
            user_state[chat_id] = "chat"
            send_message(chat_id, "💬 وضع المحادثة مفعل")
            return "ok", 200

        elif text == "/generate":
            user_state[chat_id] = "generate"
            send_message(chat_id, "🎨 أرسل وصف الصورة")
            return "ok", 200

        # ===== Generate =====

        elif text and state == "generate":
            send_message(chat_id, "⏳ جاري إنشاء الصورة...")
            try:
                img = generate_image(text)
                send_photo(chat_id, img)
            except Exception as e:
                send_message(chat_id, f"❌ {e}")
            return "ok", 200

        # ===== Chat =====

        elif text:
            reply = ask_ai(text)
            send_message(chat_id, reply)
            return "ok", 200

        return "ok", 200

    except Exception as e:
        logging.error("WEBHOOK ERROR: %s", e)
        return "error", 200

# ================== HOME ==================

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

# ================== RUN ==================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
