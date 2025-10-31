import os
import telebot
from flask import Flask, request
from gtts import gTTS
import tempfile
import openai

openai.api_key = OPENROUTER_API_KEY
openai.base_url = "https://openrouter.ai/api/v1"


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)


@app.route('/')
def home():
    return "🤖 Telegram ChatGPT Bot is running!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    json_update = request.get_json()
    if not json_update:
        return "no update", 400

    update = telebot.types.Update.de_json(json_update)
    bot.process_new_updates([update])
    return "ok", 200

@bot.message_handler(content_types=['text'])
def handle_text(message):
    try:
        prompt = message.text

        completion = client.chat.completions.create(
            model="google/gemma-7b-it",
            messages=[
                {"role": "system", "content": "You are a multilingual assistant that replies in the same language (Persian, English, or Turkish)."},
                {"role": "user", "content": prompt},
            ],
        )

        reply = completion.choices[0].message.content.strip()
        bot.send_message(message.chat.id, reply)

        # ساخت فایل صوتی
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmpfile:
            tts = gTTS(reply, lang="fa", tld="com", slow=False)
            tts.save(tmpfile.name)
            bot.send_voice(message.chat.id, voice=open(tmpfile.name, 'rb'))
            os.remove(tmpfile.name)

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ خطا: {e}")

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    bot.send_message(message.chat.id, "🎧 ویس دریافت شد، اما در حال حاضر فقط متن پشتیبانی می‌شود.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.send_message(message.chat.id, "🖼 عکس دریافت شد، فعلاً فقط متن پاسخ داده می‌شود.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
