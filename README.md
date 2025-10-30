# Telegram ChatGPT Bot (Multilingual, GPT-5)

## Deploy on Render

1. Create a new Web Service on [Render.com](https://render.com)
2. Connect your GitHub repo or upload manually
3. Set environment variables:
   - TELEGRAM_TOKEN = your_telegram_bot_token
   - OPENAI_API_KEY = your_openai_api_key
   - MODEL = gpt-5
4. Build command:
   ```bash
   pip install -r requirements.txt
   ```
   Start command:
   ```bash
   gunicorn bot:app --bind 0.0.0.0:$PORT
   ```

After deployment, set the webhook:
```
https://api.telegram.org/bot<YOUR_TELEGRAM_TOKEN>/setWebhook?url=https://your-app.onrender.com/webhook
```

Now your bot is multilingual and replies in the same language as the user!
