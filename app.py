import os
import requests
from flask import Flask, request, jsonify, send_file
from pathlib import Path
from gtts import gTTS
from pydub import AudioSegment
import io
import tempfile
import logging

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# Environment variables (set these in Render)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_API_KEY = os.environ.get("HF_API_KEY")  # optional for transcription & image captioning

TELEGRAM_API = "https://api.telegram.org"
TELEGRAM_FILE_API = "https://api.telegram.org/file/bot"

DATA_DIR = Path("/tmp/telegram_bot_data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

MODEL_ID = "google/gemma-7b-it"

def ask_openrouter(prompt):
    if not OPENROUTER_API_KEY:
        return "ℹ️ OpenRouter API key not set. Please set OPENROUTER_API_KEY in environment."
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    system_prompt = (
        "You are a helpful multilingual assistant. Detect user's language and reply naturally. "
        "Prefer Persian when input is Persian."
    )
    data = {
        "model": MODEL_ID,
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
    except Exception as e:
        app.logger.error("OpenRouter error: %s %s", getattr(resp, 'status_code', None), getattr(resp, 'text', None))
        return f"⚠️ خطا در ارتباط با OpenRouter: {e}"

def download_file(file_path):
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
    if not HF_API_KEY:
        return None
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

def tts_generate(text, lang):
    try:
        tts = gTTS(text=text, lang=lang)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tts.save(tmp.name)
            tmp_path = tmp.name
        audio = AudioSegment.from_file(tmp_path, format="mp3")
        new_sample_rate = int(audio.frame_rate * 0.90)
        lowered = audio._spawn(audio.raw_data, overrides={"frame_rate": new_sample_rate})
        lowered = lowered.set_frame_rate(22050)
        out_io = io.BytesIO()
        lowered.export(out_io, format="mp3")
        out_io.seek(0)
        return out_io
    except Exception as e:
        app.logger.error("TTS failed: %s", e)
        return None

def send_audio(chat_id, audio_bytes_io, reply_to_message_id=None):
    url = f"{TELEGRAM_API}/bot{TELEGRAM_TOKEN}/sendAudio"
    files = {"audio": ("reply.mp3", audio_bytes_io, "audio/mpeg")}
    data = {"chat_id": chat_id}
    if reply_to_message_id:
        data["reply_to_message_id"] = reply_to_message_id
    try:
        resp = requests.post(url, data=data, files=files, timeout=30)
        return resp.ok
    except Exception as e:
        app.logger.error("send_audio failed: %s", e)
        return False

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
    app.logger.info("Update received keys: %s", list(data.keys()) if data else None)
    if not data:
        return jsonify({"ok": True})

    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        reply_to = msg.get("message_id")

        if "text" in msg and msg["text"]:
            user_text = msg["text"]
            reply = ask_openrouter(user_text)
            send_message(chat_id, reply, reply_to_message_id=reply_to)
            lang = "fa"
            if any("\u0600" <= ch <= "\u06FF" for ch in user_text):
                lang = "fa"
            elif any(ch.isalpha() and ch.lower() in 'abcdefghijklmnopqrstuvwxyz' for ch in user_text):
                # simple detection between en and tr: if contains 'ğ' 'ş' etc maybe tr
                if any(c in user_text.lower() for c in 'çğıöşü'):
                    lang = 'tr'
                else:
                    lang = 'en'
            audio_io = tts_generate(reply, lang)
            if audio_io:
                send_audio(chat_id, audio_io, reply_to_message_id=reply_to)
            return jsonify({"ok": True})

        if "voice" in msg or "audio" in msg:
            file_info = msg.get("voice") or msg.get("audio") 
            file_id = file_info.get("file_id")
            gf = requests.get(f"{TELEGRAM_API}/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}", timeout=15).json()
            file_path = gf.get('result', {}).get('file_path')
            local = download_file(file_path)
            if not local:
                send_message(chat_id, "⚠️ خطا در دانلود فایل صوتی.")
                return jsonify({"ok": True})
            transcription = hf_speech_to_text(local)
            if transcription:
                reply = ask_openrouter(transcription)
                send_message(chat_id, reply, reply_to_message_id=reply_to)
                audio_io = tts_generate(reply, "fa" if any("\u0600" <= ch <= "\u06FF" for ch in transcription) else ( 'tr' if any(c in transcription.lower() for c in 'çğıöşü') else 'en'))
                if audio_io:
                    send_audio(chat_id, audio_io, reply_to_message_id=reply_to)
            else:
                send_message(chat_id, "✅ ویس دریافت شد. برای تبدیل خودکار به متن، HF_API_KEY را در متغیرها بگذارید.")
            return jsonify({"ok": True})

        if "photo" in msg:
            photos = msg["photo"]
            best = photos[-1]
            file_id = best.get("file_id")
            gf = requests.get(f"{TELEGRAM_API}/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}", timeout=15).json()
            file_path = gf.get('result', {}).get('file_path')
            local = download_file(file_path)
            if not local:
                send_message(chat_id, "⚠️ خطا در دانلود تصویر.")
                return jsonify({"ok": True})
            caption = hf_image_caption(local)
            if caption:
                reply = ask_openrouter(caption)
                send_message(chat_id, reply, reply_to_message_id=reply_to)
                audio_io = tts_generate(reply, "fa" if any("\u0600" <= ch <= "\u06FF" for ch in caption) else ('tr' if any(c in caption.lower() for c in 'çğıöşü') else 'en'))
                if audio_io:
                    send_audio(chat_id, audio_io, reply_to_message_id=reply_to)
            else:
                send_message(chat_id, "✅ عکس دریافت شد. برای فعال‌سازی توضیح‌دهی تصویر، HF_API_KEY را در متغیرها قرار دهید.")
            return jsonify({"ok": True})

        send_message(chat_id, "تنها متن، ویس و عکس پشتیبانی می‌شود.")
        return jsonify({"ok": True})

    return jsonify({"ok": True})

@app.route('/')
def home():
    return "🌍 Telegram Multilingual Bot (Gemma/OpenRouter) - running"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
