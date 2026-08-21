# services/ai_engine.py — Ultra-fast Groq + Gemini Fallback
import logging
import time
import google.generativeai as genai
from groq import AsyncGroq
from config import GEMINI_API_KEY, GROQ_API_KEY, GEMINI_MODEL, GROQ_MODEL

log = logging.getLogger(__name__)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

groq_client = AsyncGroq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


async def ask_groq(messages: list[dict]) -> str:
    """Groq API orqali ultra-tezkor javob (0.3 - 1 soniya)."""
    groq_messages = []
    for m in messages:
        role = "assistant" if m["role"] == "model" else m["role"]
        groq_messages.append({"role": role, "content": m["content"]})

    response = await groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=groq_messages,
        max_tokens=2048,
        temperature=0.7,
    )
    return response.choices[0].message.content


async def ask_gemini(messages: list[dict], image_data: bytes = None) -> str:
    """Gemini API orqali javob olish (Vision & Fallback)."""
    model = genai.GenerativeModel(GEMINI_MODEL)
    history = messages[:-1]
    last_msg = messages[-1]["content"] if messages else ""

    chat = model.start_chat(history=[
        {"role": m["role"], "parts": [m["content"]]} for m in history
    ])

    if image_data:
        import PIL.Image
        import io
        img = PIL.Image.open(io.BytesIO(image_data))
        response = await chat.send_message_async([last_msg, img])
    else:
        response = await chat.send_message_async(last_msg)

    return response.text


async def get_ai_response(
    messages: list[dict],
    image_data: bytes = None,
) -> tuple[str, str]:
    """
    Asosiy AI chaqiruvi:
    1. Rasm bo'lsa -> Gemini Vision (chunki Groq matn uchun)
    2. Matn bo'lsa -> Groq (Ultra-tezkor: 0.3s)
    3. Agar Groq xato bersa -> Gemini (Fallback)
    """
    start = time.time()

    # Rasm bo'lsa darhol Gemini'ga
    if image_data and GEMINI_API_KEY:
        try:
            text = await ask_gemini(messages, image_data)
            log.info(f"Gemini Vision javob berdi | {round(time.time() - start, 2)}s")
            return text, "gemini_vision"
        except Exception as e:
            log.error(f"Gemini Vision xatosi: {e}")

    # 1-O'rinda: Groq (Ultra-tezkor 0.3s)
    if groq_client:
        try:
            text = await ask_groq(messages)
            log.info(f"Groq (tezkor) javob berdi | {round(time.time() - start, 2)}s")
            return text, "groq"
        except Exception as e:
            log.warning(f"Groq xatosi: {e} — Gemini'ga o'tamiz...")

    # 2-O'rinda: Gemini Fallback
    if GEMINI_API_KEY:
        try:
            text = await ask_gemini(messages)
            log.info(f"Gemini (fallback) javob berdi | {round(time.time() - start, 2)}s")
            return text, "gemini"
        except Exception as e:
            log.error(f"Gemini ham xato berdi: {e}")

    return (
        "⚠️ Hozirda AI xizmatiga ulanib bo'lmadi. Iltimos, bir oz kutib qayta urinib ko'ring.",
        "none"
    )