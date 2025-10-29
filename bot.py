python-telegram-bot==20.3
openai

import os
import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# گرفتن توکن‌ها از تنظیمات Railway (Environment Variables)
TELEGRAM_TOKEN = os.getenv("8419509134:AAEKCepUil1nmIOg-ZBvfWXuCbLZAr2Ahe4")
OPENAI_API_KEY = os.getenv("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 
")

openai.api_key = OPENAI_API_KEY

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام 👋 من ربات ChatGPT هستم. هر چی بخوای بپرس!")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_message}],
            max_tokens=600,
            temperature=0.8,
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        reply = f"⚠️ خطا در ارتباط با ChatGPT:\n{e}"

    await update.message.reply_text(reply)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    print("🤖 Bot is running on Railway ...")
    app.run_polling()
