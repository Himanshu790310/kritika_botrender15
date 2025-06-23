# main.py
import os
import re
import nest_asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from gtts import gTTS
import google.generativeai as genai

nest_asyncio.apply()

# Env vars
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6138277581"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Gemini setup
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# FastAPI app
app = FastAPI()

@app.get("/")
def root():
    return {"message": "Kritika is alive!"}

# Kritika Prompt

def kritika_prompt(user_input: str) -> str:
    return f"""
You are Kritika, a warm, polite, culturally-aware AI English teacher for Hindi-speaking students.
...
"{user_input}"
"""

def get_kritika_reply(doubt: str) -> str:
    try:
        prompt = kritika_prompt(doubt)
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "Kritika thoda busy hai abhi. Thodi der baad try kariye. 🙏"

def clean_text(text):
    return re.sub(r"[*_~`#>\[\]()\-]", "", text)

def generate_voice(text, filename="kritika_reply.mp3"):
    cleaned = clean_text(text)
    tts = gTTS(cleaned, lang="hi")
    tts.save(filename)
    return filename

# Telegram App (global for webhook use)
application: Application = None

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doubt = ' '.join(context.args).strip()
    user_id = update.effective_user.id
    name = update.effective_user.full_name

    if not doubt:
        await update.message.reply_text("❓ /ask ke baad apna doubt likhiye.")
        return

    await update.message.reply_text("🧠 Kritika soch rahi hai...")
    reply = get_kritika_reply(doubt)
    audio_path = generate_voice(reply)

    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"\U0001F469‍\U0001F3EB Kritika:\n{reply}")
    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(audio_path, "rb"))

    await context.bot.send_message(chat_id=ADMIN_ID, text=f"📩 From {name} (ID: {user_id}):\n❓ {doubt}\n📘 {reply}")

@app.on_event("startup")
async def start_bot():
    global application
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("ask", ask))
    await application.bot.set_webhook(WEBHOOK_URL)

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"status": "ok"}
