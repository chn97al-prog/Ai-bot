import os
import uuid
import logging
import requests
from flask import Flask, request

# ================== ENV ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN is missing")

if not OPENAI_API_KEY:
    raise Exception("OPENAI_API_KEY is missing")

# ================== LOGGING ==================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ================== APP ==================

app = Flask(__name__)
user_state = {}

# ================== TELEGRAM ==================

def send_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        logging.error("send_message error: %s", e)

def send_photo(chat_id, photo_url):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        requests.post(url, json={"chat_id": chat_id, "photo": photo_url}, timeout=20)
    except Exception as e:
        logging.error("send_photo error: %s", e)

# ================== OPENAI CHAT ==================

def ask_ai(prompt):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }

    res = requests.post(url, headers=headers, json=data, timeout=20)

    if res.status_code != 200:
        return f"❌ خطأ: {res.text}"

    result = res.json()
    return result["choices"][0]["message"]["content"]

# ================== IMAGE ==================

def generate_image(prompt):
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    data = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "size": "1024x1024"
    }

    res = requests.post(url, headers=headers, json=data, timeout=30)

    if res.status_code != 200:
        raise Exception(res.text)

    result = res.json()
    return result["data"][0]["url"]

# ================== DOWNLOAD ==================

def download_telegram_file(file_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile"
    res = requests.get(url, params={"file_id": file_id}).json()

    file_path = res["result"]["file_path"]
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

    file_data = requests.get(file_url)

    file_name = f"{uuid.uuid4().hex}.png"
    with open(file_name, "wb") as f:
        f.write(file_data.content)

    return file_name

# ================== EDIT IMAGE ==================

def edit_image(image_path, prompt):
    url = "https://api.openai.com/v1/images/edits"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    with open(image_path, "rb") as f:
        files = {"image": f}
        data = {
            "model": "gpt-image-1",
            "prompt": prompt
        }

        res = requests.post(url, headers=headers, files=files, data=data)

    if res.status_code != 200:
        raise Exception(res.text)

    result = res.json()
    return result["data"][0]["url"]

# ================== WEBHOOK ==================

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        logging.info("Incoming update: %s", data)

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
            send_message(chat_id, "👋 أهلاً بك\n\n/chat\n/generate\n/edit")
            return "ok", 200

        elif text == "/chat":
            user_state[chat_id] = "chat"
            send_message(chat_id, "💬 وضع المحادثة مفعل")
            return "ok", 200

        elif text == "/generate":
            user_state[chat_id] = "generate"
            send_message(chat_id, "🎨 أرسل وصف الصورة")
            return "ok", 200

        elif text == "/edit":
            user_state[chat_id] = "edit"
            send_message(chat_id, "🖼️ أرسل صورة مع وصف")
            return "ok", 200

        # ===== Edit Image =====

        if photo and state == "edit":
            send_message(chat_id, "⏳ جاري التعديل...")
            try:
                file_id = photo[-1]["file_id"]
                image_path = download_telegram_file(file_id)
                prompt = msg.get("caption", "Edit this image")
                edited_url = edit_image(image_path, prompt)
                send_photo(chat_id, edited_url)
                os.remove(image_path)
            except Exception as e:
                send_message(chat_id, f"❌ خطأ: {e}")

            return "ok", 200

        # ===== Generate Image =====

        elif text and state == "generate":
            send_message(chat_id, "⏳ جاري إنشاء الصورة...")
            try:
                img = generate_image(text)
                send_photo(chat_id, img)
            except Exception as e:
                send_message(chat_id, f"❌ خطأ: {e}")

            return "ok", 200

        # ===== Chat =====

        elif text:
            reply = ask_ai(text)
            send_message(chat_id, reply)
            return "ok", 200

        return "ok", 200

    except Exception as e:
        logging.error("WEBHOOK ERROR: %s", e)
        return "error", 500

# ================== HOME ==================

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

# ================== RUN ==================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
