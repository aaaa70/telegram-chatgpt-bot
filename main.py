import os
import requests
from flask import Flask, request
from gtts import gTTS
import tempfile

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_TOKEN = os.environ.get("OPENROUTER_TOKEN")
BOT_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
MODEL = "google/gemma-7b-it"

def get_chat_response(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }
    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]

def send_voice(chat_id, text):
    tts = gTTS(text=text, lang="fa", tld="com")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tts.save(tmp.name)
        with open(tmp.name, "rb") as f:
            files = {"voice": f}
            requests.post(f"{BOT_URL}/sendVoice", data={"chat_id": chat_id}, files=files)
    os.remove(tmp.name)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"]["text"]
        try:
            reply = get_chat_response(user_text)
        except Exception as e:
            reply = f"❌ خطا در ارتباط با OpenRouter: {e}"
        requests.post(f"{BOT_URL}/sendMessage", data={"chat_id": chat_id, "text": reply})
        try:
            send_voice(chat_id, reply)
        except Exception as e:
            requests.post(f"{BOT_URL}/sendMessage", data={"chat_id": chat_id, "text": f'⚠️ خطا در تولید صدا: {e}'})
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
