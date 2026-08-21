# services/ai_engine.py — Gemini + Groq + Fallback Engine
import logging
import time
import google.generativeai as genai
from groq import AsyncGroq
from config import GEMINI_API_KEY, GROQ_API_KEY, GEMINI_MODEL, GROQ_MODEL

log = logging.getLogger(__name__)

# API klientlarini sozlash
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

groq_client = AsyncGroq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


async def ask_gemini(messages: list[dict], image_data: bytes = None) -> str:
    """Gemini API orqali javob olish."""
    model = genai.GenerativeModel(GEMINI_MODEL)
    history = messages[:-1]  # Oxirgi user xabarsiz
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


async def ask_groq(messages: list[dict]) -> str:
    """Groq API orqali javob olish (Fallback)."""
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


async def get_ai_response(
    messages: list[dict],
    image_data: bytes = None,
) -> tuple[str, str]:
    """
    Asosiy AI javob funksiyasi.
    Gemini > Groq (fallback) tartibida urinadi.
    Returns: (response_text, model_used)
    """
    start = time.time()

    # --- Gemini ---
    if GEMINI_API_KEY:
        try:
            text = await ask_gemini(messages, image_data)
            latency = round(time.time() - start, 2)
            log.info(f"Gemini javob berdi | {latency}s")
            return text, "gemini"
        except Exception as e:
            log.warning(f"Gemini xatosi: {e} — Groq'ga o'tamiz...")

    # --- Groq Fallback ---
    if groq_client:
        try:
            text = await ask_groq(messages)
            latency = round(time.time() - start, 2)
            log.info(f"Groq (fallback) javob berdi | {latency}s")
            return text, "groq"
        except Exception as e:
            log.error(f"Groq ham xato berdi: {e}")

    # --- Ikkalasi ham ishlamasa ---
    return (
        "?? Hozirda AI xizmatiga ulanib bo'lmadi. Iltimos, bir oz kutib qayta urinib ko'ring.",
        "none"
    )
