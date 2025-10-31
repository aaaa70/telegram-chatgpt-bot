import os
import requests
from flask import Flask, request, jsonify
from pathlib import Path

app = Flask(__name__)

# Environment variables
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_API_KEY = os.environ.get("HF_API_KEY")  # Optional: Hugging Face API key for speech/image processing

TELEGRAM_API = "https://api.telegram.org"
TELEGRAM_FILE_API = "https://api.telegram.org/file/bot"

# Ensure data directory exists
DATA_DIR = Path("/tmp/telegram_bot_data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def ask_openrouter(prompt):
    if not OPENROUTER_API_KEY:
        return "ℹ️ OpenRouter API key not set. Please set OPENROUTER_API_KEY in environment."
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    system_prompt = (
        "You are a multilingual assistant that automatically detects the user's language "
        "and responds naturally in that same language. If the user's message is Persian, "
        "prefer to answer in Persian. Keep answers concise and friendly."
    )
    data = {
        "model": "meta-llama/Meta-Llama-3-70B-Instruct",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    resp = requests.post(url, headers=headers, json=data, timeout=60)
    try:
        j = resp.json()
        return j["choices"][0]["message"]["content"]
    except Exception:
        return f"⚠️ خطا در ارتباط با OpenRouter: HTTP {resp.status_code} - {resp.text}"

def download_file(file_path):
    # file_path is the "file_path" returned by getFile
    # returns local saved path or None
    if not file_path:
        return None
    file_url = f"{TELEGRAM_FILE_API}{TELEGRAM_TOKEN}/{file_path}"
    local_name = DATA_DIR / Path(file_path).name
    try:
        r = requests.get(file_url, stream=True, timeout=30)
        r.raise_for_status()
        with open(local_name, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return str(local_name)
    except Exception as e:
        app.logger.error("download_file failed: %s", e)
        return None

def hf_speech_to_text(local_path):
    """
    Optional: If HF API key provided, send audio bytes to a Hugging Face speech-to-text model.
    This function is optional and best-effort — some models accept ogg/opus, others need wav.
    If HF_API_KEY is not set, returns None.
    """
    if not HF_API_KEY:
        return None
    # Example: use 'openai/whisper-large' or other speech model on Hugging Face inference
    hf_url = "https://api-inference.huggingface.co/models/openai/whisper-large"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    try:
        with open(local_path, "rb") as f:
            data = f.read()
        resp = requests.post(hf_url, headers=headers, data=data, timeout=120)
        j = resp.json()
        if isinstance(j, dict) and "text" in j:
            return j["text"]
        if isinstance(j, dict) and "transcription" in j:
            return j["transcription"]
        if isinstance(j, str):
            return j
        return None
    except Exception as e:
        app.logger.error("hf_speech_to_text failed: %s", e)
        return None

def hf_image_caption(local_path):
    """
    Optional: If HF API key provided, send image bytes to a captioning model (e.g., blip).
    Returns caption text or None.
    """
    if not HF_API_KEY:
        return None
    hf_url = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-large"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    try:
        with open(local_path, "rb") as f:
            data = f.read()
        resp = requests.post(hf_url, headers=headers, data=data, timeout=120)
        j = resp.json()
        if isinstance(j, dict) and "error" in j:
            return None
        if isinstance(j, list) and len(j) > 0 and "generated_text" in j[0]:
            return j[0]["generated_text"]
        if isinstance(j, dict) and "caption" in j:
            return j["caption"]
        return None
    except Exception as e:
        app.logger.error("hf_image_caption failed: %s", e)
        return None

def send_message(chat_id, text, reply_to_message_id=None):
    url = f"{TELEGRAM_API}/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        app.logger.error("send_message failed: %s", e)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    app.logger.info("Update received: %s", data and list(data.keys()))
    if not data:
        return jsonify({"ok": True})

    # Handle text messages
    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        reply_to = msg.get("message_id")
        # Text
        if "text" in msg and msg["text"]:
            user_text = msg["text"]
            app.logger.info("Text message: %s", user_text[:80])
            reply = ask_openrouter(user_text)
            send_message(chat_id, reply, reply_to_message_id=reply_to)
            return jsonify({"ok": True})

        # Voice / Audio
        if "voice" in msg or "audio" in msg:
            file_info = msg.get("voice") or msg.get("audio")
            file_id = file_info.get("file_id")
            # getFile to obtain file_path
            gf = requests.get(f"{TELEGRAM_API}/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}", timeout=15).json()
            file_path = gf.get("result", {}).get("file_path")
            local = download_file(file_path)
            if not local:
                send_message(chat_id, "⚠️ خطا در دانلود فایل صوتی.")
                return jsonify({"ok": True})
            # Try HF transcription if available
            transcription = hf_speech_to_text(local)
            if transcription:
                reply = ask_openrouter(transcription)
                send_message(chat_id, reply, reply_to_message_id=reply_to)
            else:
                send_message(chat_id, "✅ ویس دریافت شد. برای فعال‌سازی تبدیل گفتار به متن، متغیر محیطی HF_API_KEY را با کلید Hugging Face قرار دهید.")
            return jsonify({"ok": True})

        # Photos
        if "photo" in msg:
            photos = msg["photo"]
            # choose highest resolution
            best = photos[-1]
            file_id = best.get("file_id")
            gf = requests.get(f"{TELEGRAM_API}/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}", timeout=15).json()
            file_path = gf.get("result", {}).get("file_path")
            local = download_file(file_path)
            if not local:
                send_message(chat_id, "⚠️ خطا در دانلود تصویر.")
                return jsonify({"ok": True})
            caption = hf_image_caption(local)
            if caption:
                reply = ask_openrouter(caption)
                send_message(chat_id, reply, reply_to_message_id=reply_to)
            else:
                send_message(chat_id, "✅ عکس دریافت شد. برای فعال‌سازی توضیح‌دهی تصویر، متغیر محیطی HF_API_KEY را با کلید Hugging Face قرار دهید.")
            return jsonify({"ok": True})

        # Other types
        send_message(chat_id, "تنها پیام‌های متنی، ویس و عکس پشتیبانی می‌شوند (در حال حاضر).")
        return jsonify({"ok": True})

    return jsonify({"ok": True})

@app.route('/')
def home():
    return "🌍 Telegram Multilingual Bot (OpenRouter chat) - running"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
