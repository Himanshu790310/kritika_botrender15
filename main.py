import os
import re
import asyncio
import nest_asyncio
from gtts import gTTS
from fastapi import FastAPI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import google.generativeai as genai

# Enable nested async (for running in notebooks or certain servers)
nest_asyncio.apply()

# Load credentials from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6138277581"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Setup Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# FastAPI app
app = FastAPI()

@app.get("/")
def root():
    return {"message": "Kritika is running 💬"}

# 🎯 Prompt function
def kritika_prompt(user_input: str) -> str:
    return f"""
You are Kritika, a warm, polite, culturally-aware AI English teacher for Hindi-speaking students.

Your role:
- Reply in Hinglish (90% Hindi in Roman + 10% English) if the question is in Hindi
- If the question is in English, reply fully in English
- Explain grammar using formula + Roman Hindi explanation
- Provide 3 to 5 simple examples
- Encourage and gently correct mistakes
- Use Indian examples (e.g., mandir instead of church)

DO NOT use difficult words or give too much theory.
Avoid religious/political/romantic content.

Here is the student question:
"{user_input}"

Reply in the style of Kritika 👩🏻‍🏫
End your answer with:
"Aur koi doubt hai?" or "Main aur madad kar sakti hoon?"
"""

# 💬 Get Gemini response
def get_kritika_reply(doubt: str) -> str:
    prompt = kritika_prompt(doubt)
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return "Kritika thoda busy hai abhi. Thodi der baad try kariye. 🙏"

# 🗣️ Clean audio text and create voice
def clean_text(text):
    return re.sub(r"[*_~`#>\[\]()\-]", "", text)

def generate_voice(text, filename="kritika_reply.mp3"):
    cleaned = clean_text(text)
    tts = gTTS(cleaned, lang="hi")
    tts.save(filename)
    return filename

# 📥 Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Namaste! Main Kritika hoon — aapki English teacher. 💬\n"
        "Aap direct apna doubt bhej sakte ho, bina kisi command ke.\n"
        "Jaise:\n- \"Present perfect tense kya hota hai?\"\n- \"Mujhe translation ka rule samjhao\"\n\n"
        "Shuru karein? 😊"
    )

# 💬 Any message = doubt
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doubt = update.message.text.strip()
    user_id = update.effective_user.id
    name = update.effective_user.full_name

    if not doubt:
        return

    await update.message.reply_text("🧠 Kritika soch rahi hai...")

    reply = get_kritika_reply(doubt)
    audio_path = generate_voice(reply)

    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"👩🏻‍🏫 Kritika:\n{reply}")
    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(audio_path, "rb"))

    await context.bot.send_message(chat_id=ADMIN_ID, text=f"📩 New doubt from {name} (ID: {user_id}):\n❓ {doubt}\n📘 {reply}")

# 🔁 Run on startup
@app.on_event("startup")
async def start_bot():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    asyncio.create_task(application.run_polling())
