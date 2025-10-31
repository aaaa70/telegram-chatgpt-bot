# Telegram Multilingual Voice Bot (OpenRouter Gemma) - Docker-ready for Render

## What's inside
- app.py (Flask webhook handler)
- requirements.txt
- Dockerfile (installs ffmpeg)
- README.md

## Deploy on Render (Docker)
1. Push repository to GitHub.
2. On Render, create a **New Web Service** -> Connect GitHub repo.
3. Choose **Docker** as the environment.
4. Add Environment Variables in Render -> Settings:
   - OPENROUTER_API_KEY = sk-or-...
   - TELEGRAM_TOKEN = bot...
   - HF_API_KEY = hf_... (optional)
5. Deploy. After successful build, set Telegram webhook:
   https://api.telegram.org/bot<TELEGRAM_TOKEN>/setWebhook?url=https://<your-render-url>/webhook

## Notes
- pydub requires ffmpeg; Dockerfile installs it.
- gTTS requires network access to Google's TTS backend.
- If you want higher-quality TTS or offline TTS, consider ElevenLabs or local TTS engines and adjust code.
