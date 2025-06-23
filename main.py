import os
import re
import asyncio
import nest_asyncio
from gtts import gTTS
from fastapi import FastAPI
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)
import google.generativeai as genai

# Allow nested async in environments like notebooks or functions
nest_asyncio.apply()

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6138277581"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini model setup
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# FastAPI instance
app = FastAPI()

@app.get("/")
def root():
    return {"message": "🌟 Kritika is Live and Ready to Teach!"}

# Prompt template for Kritika
def kritika_prompt(user_input: str) -> str:
    return f"""
# 👩‍🏫 Kritika - Your Friendly English Teacher for Hindi Speakers

## Role
You're Kritika — a calm, clear, friendly AI English teacher who helps Hindi-speaking learners with English doubts.

## Rules:
- If input is Hindi → respond in Hinglish (90% Roman Hindi + 10% English)
- If input is English → respond in simple, correct English
- Use real-life Indian examples, grammar formulas, and 3–5 short examples
- Add encouragement and explain gently
- End with: "Aur koi doubt hai?" or "Main aur madad kar sakti hoon?"
- Response should sound good in voice (avoid `**`, special markdown)

Here is the user’s doubt:
\"\"\"{user_input}\"\"\"
"""

# Generate reply using Gemini
def get_kritika_reply(doubt: str) -> str:
    prompt = kritika_prompt(doubt)
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return "Kritika thoda busy hai abhi. Thodi der baad try kariye. 🙏"

# Clean text for gTTS
def clean_text(text):
    return re.sub(r"[*_~`#>\[\]()\-]", "", text)

# Convert text to speech
def generate_voice(text, filename="kritika_reply.mp3"):
    cleaned = clean_text(text)
    tts = gTTS(cleaned, lang="hi")
    tts.save(filename)
    return filename

# Handler for any text message
def is_first_message(context):
    return not context.chat_data.get("welcomed", False)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doubt = update.message.text.strip()
    user_id = update.effective_user.id
    name = update.effective_user.full_name

    if not doubt:
        await update.message.reply_text("❓ Kya samjhaun? Sawal likhiye.")
        return

    if is_first_message(context):
        await update.message.reply_text("Namaste! Main Kritika hoon 👩‍🏫 Aapka doubt suna ja raha hai...")
        context.chat_data["welcomed"] = True
    else:
        await update.message.reply_text("🧠 Kritika soch rahi hai...")

    reply = get_kritika_reply(doubt)
    audio_path = generate_voice(reply)

    await update.message.reply_text(f"👩‍🏫 Kritika:\n{reply}")
    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(audio_path, "rb"))

    # Notify Admin
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📬 New doubt from {name} (ID: {user_id}):\n💭 {doubt}\n📘 {reply}"
    )

# Start both FastAPI and Telegram bot
@app.on_event("startup")
async def start_bot():
    app_bot = Application.builder().token(BOT_TOKEN).build()
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    asyncio.create_task(app_bot.run_polling())

# 👇 Required for Cloud Run or local run
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
