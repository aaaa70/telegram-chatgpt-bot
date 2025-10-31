import os
import requests
from flask import Flask, request, jsonify
from gtts import gTTS
import tempfile
import logging

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

if not TELEGRAM_TOKEN or not OPENROUTER_API_KEY:
    app.logger.warning("TELEGRAM_TOKEN or OPENROUTER_API_KEY not set. Set env vars in Render settings.")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

MODEL_ID = "google/gemma-7b-it"

def ask_openrouter(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": "You are a helpful multilingual assistant. Prefer Persian when input is Persian."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=60)
        resp.raise_for_status()
        j = resp.json()
        return j["choices"][0]["message"]["content"]
    except Exception as e:
        app.logger.error("OpenRouter request failed: %s %s", getattr(e, "response", None), e)
        return None

def send_text(chat_id, text, reply_to_message_id=None):
    try:
        payload = {"chat_id": chat_id, "text": text}
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=15)
    except Exception as e:
        app.logger.error("send_text failed: %s", e)

def send_audio(chat_id, audio_bytes_io, reply_to_message_id=None):
    try:
        files = {"audio": ("reply.mp3", audio_bytes_io, "audio/mpeg")}
        data = {"chat_id": str(chat_id)}
        if reply_to_message_id:
            data["reply_to_message_id"] = str(reply_to_message_id)
        resp = requests.post(f"{TELEGRAM_API}/sendAudio", data=data, files=files, timeout=30)
        app.logger.info("sendAudio status: %s", resp.status_code)
    except Exception as e:
        app.logger.error("send_audio failed: %s", e)

@app.route("/", methods=["GET"])
def home():
    return "🤖 Telegram Persian TTS Bot (OpenRouter) is running", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    app.logger.info("Update received keys: %s", list(data.keys()) if data else None)
    if not data:
        return jsonify({"ok": True})

    # Only handle message updates
    message = data.get("message") or data.get("edited_message")
    if not message:
        return jsonify({"ok": True})

    chat_id = message["chat"]["id"]
    reply_to = message.get("message_id")

    # If text message
    text = message.get("text")
    if text:
        app.logger.info("User text: %s", text[:120])
        reply = ask_openrouter(text)
        if not reply:
            send_text(chat_id, "⚠️ خطا در دریافت پاسخ از مدل. لطفاً بعداً تلاش کنید.", reply_to_message_id=reply_to)
            return jsonify({"ok": True})

        # Send text response
        send_text(chat_id, reply, reply_to_message_id=reply_to)

        # Generate Persian TTS (gTTS uses 'fa' for Persian)
        try:
            tts = gTTS(text=reply, lang="fa")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                tts.save(tmp.name)
                tmp.seek(0)
                with open(tmp.name, "rb") as f:
                    audio_bytes = f.read()
            # send audio as file-like object
            from io import BytesIO
            send_audio(chat_id, BytesIO(audio_bytes), reply_to_message_id=reply_to)
        except Exception as e:
            app.logger.error("TTS generation failed: %s", e)
            send_text(chat_id, "⚠️ خطا در تولید صدای ربات.", reply_to_message_id=reply_to)

        return jsonify({"ok": True})

    # If voice message: notify user that transcription optional (HF not set)
    if "voice" in message or "audio" in message:
        send_text(chat_id, "✅ ویس دریافت شد — در نسخه فعلی فقط متن و ویس خروجی پشتیبانی می‌شود (برای تبدیل خودکار ویس به متن، HF_API_KEY را اضافه کنید).", reply_to_message_id=reply_to)
        return jsonify({"ok": True})

    # If photo
    if "photo" in message:
        send_text(chat_id, "✅ تصویر دریافت شد — برای فعال‌سازی توضیح تصویر، HF_API_KEY را اضافه کنید.", reply_to_message_id=reply_to)
        return jsonify({"ok": True})

    send_text(chat_id, "پیام دریافت شد (نوع پشتیبانی نشده).", reply_to_message_id=reply_to)
    return jsonify({"ok": True})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
