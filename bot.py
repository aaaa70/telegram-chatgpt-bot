import os
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = os.environ.get("MODEL", "gpt-5")
SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    "You are a helpful AI assistant. Detect the user's language and reply in the same language clearly and naturally."
)
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1000"))
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.2"))

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    logger.error("Please set TELEGRAM_TOKEN and OPENAI_API_KEY environment variables.")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

def send_telegram_chat_action(chat_id, action="typing"):
    url = f"{TELEGRAM_API_URL}/sendChatAction"
    try:
        requests.post(url, json={"chat_id": chat_id, "action": action}, timeout=5)
    except Exception as e:
        logger.warning("sendChatAction failed: %s", e)

def send_telegram_message(chat_id, text, reply_to_message_id=None):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    try:
        r = requests.post(url, json=payload, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.exception("Failed to send message to Telegram: %s", e)
        return None

def query_openai(user_text):
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.exception("OpenAI request failed: %s", e)
        return "متاسفم — خطایی در پردازش رخ داد."

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    logger.info("Update received: %s", update)

    if "message" in update:
        message = update["message"]
        text = message.get("text", "")
        chat_id = message["chat"]["id"]
        message_id = message.get("message_id")

        if not text:
            send_telegram_message(chat_id, "فقط پیام‌های متنی پشتیبانی می‌شود.", reply_to_message_id=message_id)
            return jsonify({"ok": True})

        send_telegram_chat_action(chat_id, "typing")

        try:
            start = time.time()
            reply = query_openai(text)
            elapsed = time.time() - start
            logger.info("OpenAI replied in %.2fs", elapsed)
        except Exception as e:
            logger.exception("Error querying OpenAI: %s", e)
            reply = "خطا در تماس با OpenAI."

        send_telegram_message(chat_id, reply, reply_to_message_id=message_id)

    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
