# Telegram Multilingual Voice Bot (OpenRouter Gemma) - Ready for Render

## Features
- Multilingual chat using OpenRouter model `google/gemma-7b-it`
- Default replies in Persian when input is Persian
- Voice message transcription (optional) via Hugging Face Inference API (set HF_API_KEY)
- Photo captioning (optional) via Hugging Face Inference API (set HF_API_KEY)
- TTS replies using gTTS with a slight pitch-down to resemble a male voice
- Deployable on Render

## Files
- `app.py` - main Flask app and Telegram webhook handler
- `requirements.txt` - Python dependencies
- `README.md` - this file

## Setup (Render)
1. Create a GitHub repo and push these files, or upload the ZIP to Render.
2. In Render, create a **Web Service** and connect your repo.
3. Build command:
   ```bash
   pip install -r requirements.txt
   ```
4. Start command:
   ```bash
   gunicorn app:app --bind 0.0.0.0:$PORT
   ```
5. Environment Variables (in Render -> Service -> Settings -> Environment):
   - `OPENROUTER_API_KEY` = your OpenRouter key (sk-or-...)
   - `TELEGRAM_TOKEN` = your Telegram bot token (from BotFather)
   - Optional:
     - `HF_API_KEY` = Hugging Face API key (to enable voice transcription & image captioning)

## Notes
- pydub requires `ffmpeg` on the system to process audio. On Render you may need to enable global build scripts or use a custom Docker image with ffmpeg installed.
- gTTS uses Google Translate TTS; network access is required.
