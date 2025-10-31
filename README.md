# Telegram Multilingual Bot (OpenRouter) - Ready for Render

## Features
- Multilingual chat using **OpenRouter** (Llama 3)
- Default replies in **Persian** when user writes Persian
- Detects and downloads **voice messages** and **photos**
- Optional: Speech-to-text and image captioning using **Hugging Face Inference API**
  (set `HF_API_KEY` environment variable to enable automatic transcription/captioning)

## Files
- `app.py` - main Flask app and Telegram webhook handler
- `requirements.txt` - Python dependencies
- `README.md` - this file

## Setup (Render)
1. Create a GitHub repo and push these files, or upload the ZIP to Render.
2. In Render, create a **Web Service** and connect your repo.
3. Build command:
   ```
   pip install -r requirements.txt
   ```
4. Start command:
   ```
   gunicorn app:app --bind 0.0.0.0:$PORT
   ```
5. Environment Variables (in Render -> Service -> Settings -> Environment):
   - `OPENROUTER_API_KEY` = your OpenRouter key (sk-or-...)
   - `TELEGRAM_TOKEN` = your Telegram bot token (from BotFather)
   - Optional:
     - `HF_API_KEY` = Hugging Face API key (to enable voice transcription & image captioning)

## Webhook
Set webhook once your service is live:
```
https://api.telegram.org/bot<YOUR_TELEGRAM_TOKEN>/setWebhook?url=https://<your-render-url>/webhook
```

## Notes & Next steps
- This implementation **always** handles text via OpenRouter.
- Voice and image processing are optional and use Hugging Face if `HF_API_KEY` is present.
- If you want automatic, higher-quality transcription (Whisper) or image understanding via other paid APIs, provide corresponding API keys and I can update the code.
- On Render you may need to ensure `ffmpeg` is available if you plan to convert audio formats.
