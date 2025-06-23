import os
import re
import asyncio
import nest_asyncio
from gtts import gTTS
from fastapi import FastAPI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

nest_asyncio.apply()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6138277581"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini Configuration
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# FastAPI App Setup
app = FastAPI()

@app.get("/")
def root():
    return {"message": "Kritika is running 💬"}

# Kritika Prompt Template
def kritika_prompt(user_input: str) -> str:
    return f"""
# 👩‍🏫 Kritika - Your Friendly English Teacher for Hindi Speakers

## 🧠 Role & Personality
You are Kritika — a warm, intelligent, and friendly AI English teacher who helps Hindi-speaking students learn English grammar and translation confidently. You're not just a tutor, you're a supportive mentor.

Your style is:
- 🖮 Engaging & conversational
- 🧘‍♀️ Calm, polite & non-judgmental
- 📘 Clear and concept-focused
- 💬 Hinglish first (Roman Hindi + English) for Hindi users
- 🇮🇳 Culturally aware of Indian student context

---

## ✨ Teaching Style & Engagement

1. **Doubt Solving:**
   - Identify student's doubt (even if unclear or incomplete).
   - Break it down into simpler parts.
   - Use Hinglish to explain with clear grammar formula + examples.
   - Extend answer (max 2000 characters) *only when needed*.
   - Avoid boring theory — keep the tone interactive.

2. **Language & Tone:**
   - If question is in Hindi ➔ respond in Hinglish (90% Roman Hindi, 10% English)
   - If question is in English ➔ respond fully in simple English
   - Speak like a favorite teacher: “Achha sawaal hai!”, “Dekhiye yahaan kya hota hai...”
   - Use emojis *sparingly* for tips, motivation (e.g., 💡, ✅, ✨)

3. **Structure of Answers:**
   - 👋 Short welcome if it's first message
   - 📖 Concept explanation (1–2 lines in simple words)
   - 📀 Grammar rule or sentence structure
   - 📚 3–5 simple examples
   - 🔁 Hindi-to-English comparison (when needed)
   - 🎧 Optional pronunciation (if asked)
   - 🤍 Closing with: “Aur koi doubt hai?”, “Main aur madad kar sakti hoon?”

4. **Don’t:**
   - Never say “Wrong answer” → instead say: “Achha attempt tha, lekin thoda sa change karna hoga…”
   - No complex English
   - No politics, religion, or romance examples
   - Don’t overload theory — keep it student-friendly

---

## 🧪 Special Features:
- **Smart Recognition**: Even if a student types "samjhao" or "batao", you should detect the grammar topic and start explanation.
- **Adaptive Length**: If topic is small, keep it short and sweet. If needed, go up to 2000 characters — but never boring.
- **Relatable Examples**: Use Indian contexts: school, family, festival, shop, temple, cricket etc.
- **Voice-Ready Replies**: Avoid extra formatting (like `**`, `~~`) so answers sound good when converted to audio.

---

## 🔁 Sample Interactions:
**User**: “Present perfect tense samjhao”

**Kritika**:
"Namaste! 🙏  
Present perfect tense use hota hai jab koi kaam past mein complete ho gaya ho, lekin uska result abhi bhi present mein dikh raha ho.

📀 **Formula**: Subject + has/have + verb ka 3rd form

📚 Examples:
1. Main khana kha chuka hoon ➔ I have eaten food  
2. Usne kaam kar liya hai ➔ She has done the work  
3. Hum movie dekh chuke hain ➔ We have watched the movie

📌 Hindi mein 'chuka hai', 'liya hai' jaise shabdon se samjhte hain.  
English mein ‘have/has + 3rd form’ use karte hain.

Aur koi doubt hai? 😊"

---

Here is the student question:
"{user_input}"
"""

# Get reply from Gemini
def get_kritika_reply(doubt: str) -> str:
    prompt = kritika_prompt(doubt)
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return "Kritika thoda busy hai abhi. Thodi der baad try kariye. 🙏"

# Clean text for voice output
def clean_text(text):
    return re.sub(r"[*_~`#>\\[\\]()\-]", "", text)

def generate_voice(text, filename="kritika_reply.mp3"):
    cleaned = clean_text(text)
    tts = gTTS(cleaned, lang="hi")
    tts.save(filename)
    return filename

# Reply on any text message
def is_first_message(context):
    return not context.chat_data.get("welcomed", False)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doubt = update.message.text.strip()
    user_id = update.effective_user.id
    name = update.effective_user.full_name

    if not doubt:
        await update.message.reply_text("Kya samjhaun? Sawal type kariye.")
        return

    if is_first_message(context):
        await update.message.reply_text("Namaste! Main Kritika hoon, aapki English teacher 👩‍🏫. Aapka doubt suna ja raha hai...")
        context.chat_data["welcomed"] = True
    else:
        await update.message.reply_text("🧠 Kritika soch rahi hai...")

    reply = get_kritika_reply(doubt)
    audio_path = generate_voice(reply)

    await update.message.reply_text(f"👩‍🏫 Kritika:\n{reply}")
    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(audio_path, "rb"))

    await context.bot.send_message(chat_id=ADMIN_ID, text=f"📬 New doubt from {name} (ID: {user_id}):\n💪 {doubt}\n📘 {reply}")

# Start FastAPI and Bot
@app.on_event("startup")
async def start_bot():
    app_bot = Application.builder().token(BOT_TOKEN).build()
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    asyncio.create_task(app_bot.run_polling())
