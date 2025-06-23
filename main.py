import os
import re
import asyncio
import logging
from gtts import gTTS
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import google.generativeai as genai

# STEP 3: Logging and event loop patch
logging.basicConfig(level=logging.INFO)

try:
    import nest_asyncio
    nest_asyncio.apply()
except:
    pass  # Not needed outside Colab

# STEP 4: Configuration
BOT_TOKEN = "7988273088:AAGhxSxjCK0H1qg51tEaf4WviU9hSF1dmfc"  # Replace with your bot token
ADMIN_ID = 6138277581                                          # Your Telegram ID
GEMINI_API_KEY = "AIzaSyDc6wrTkV2k4AWl72NZxET6URrXCbM8haM"      # Replace with your Gemini key

# STEP 5: Gemini Setup
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash-latest")

# STEP 6: Kritika prompt logic
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

# STEP 7: Get response from Gemini
def get_kritika_reply(doubt: str) -> str:
    prompt = kritika_prompt(doubt)
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return "Kritika thoda busy hai abhi. Thodi der baad try kariye. 🙏"

# STEP 8: Clean markdown for gTTS
def clean_text(text):
    return re.sub(r"[*_~`#>\[\]()\-]", "", text)

def generate_voice(text, filename="kritika_reply.mp3"):
    cleaned_text = clean_text(text)
    tts = gTTS(cleaned_text, lang="hi")
    tts.save(filename)
    return filename

# STEP 9: /ask handler
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doubt = ' '.join(context.args).strip()
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name

    if not doubt:
        await update.message.reply_text("❓ /ask ke baad apna doubt likhiye.\nJaise: /ask Present perfect tense samjhao")
        return

    await update.message.reply_text("🧠 Kritika soch rahi hai... thoda sa wait kariye...")

    reply = get_kritika_reply(doubt)
    audio_path = generate_voice(reply)

    # Send response to student
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"👩🏻‍🏫 Kritika:\n{reply}")
    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(audio_path, "rb"))

    # Send copy to admin
    admin_message = (
        f"📩 New doubt received by Kritika:\n"
        f"👤 From: {user_name} (ID: {user_id})\n"
        f"❓ Doubt: {doubt}\n\n"
        f"📘 Kritika's Response:\n{reply}"
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)

# STEP 10: Main bot runner
async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("ask", ask))

    print("✅ Kritika is now live with Gemini 1.5 Flash and audio replies!")
    await app.run_polling()

# STEP 11: Launch bot
if __name__ == "__main__":
    asyncio.run(main())
