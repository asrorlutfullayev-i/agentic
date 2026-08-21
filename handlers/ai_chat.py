# handlers/ai_chat.py — Tezkor, Real-time Web va Xavfsiz AI Handler
import re
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest
from services.db import get_or_create_user, save_message, add_reminder
from services.ai_engine import get_ai_response
from services.context_builder import build_context
from services.memory_manager import memory_manager
from services.tools.web_search import web_search, search_and_augment
from services.tools.github_search import github_search
from services.tools.arxiv_search import arxiv_search
from services.tools.kaggle_search import kaggle_search
from services.tools.calculator import calculate
from services.tools.file_analysis import extract_text_from_file
from config import TIMEZONE, MAX_FILE_SIZE_MB
import pytz

log = logging.getLogger(__name__)
router = Router()
tz = pytz.timezone(TIMEZONE)


async def safe_reply(message: Message, text: str, thinking_msg: Message = None):
    """Xabarni xavfsiz yuborish (Markdown xatolarini ushlaydi va uzun xabarlarni bo'ladi)."""
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)] if len(text) > 4000 else [text]

    for idx, chunk in enumerate(chunks):
        try:
            if idx == 0 and thinking_msg:
                await thinking_msg.edit_text(chunk, parse_mode="Markdown")
            else:
                await message.answer(chunk, parse_mode="Markdown")
        except TelegramBadRequest:
            if idx == 0 and thinking_msg:
                await thinking_msg.edit_text(chunk, parse_mode=None)
            else:
                await message.answer(chunk, parse_mode=None)


def _detect_intent(text: str) -> str:
    t = text.lower()
    # Eslatma va taymer iboralari
    time_words = ["daqiqa", "minut", "min", "soat", "ertaga", "indinga", "sekund"]
    action_words = ["eslat", "eslatma", "xabar yubor", "yoz", "ayt", "reminder", "ogohlantir", "kn", "keyin"]

    if (any(w in t for w in action_words) and any(w in t for w in time_words)) or ("daqiqadan" in t or "minutdan" in t or "soatdan" in t):
        return "reminder"

    if any(w in t for w in ["hisobla", "hisopla", "necha", "qo'sh", "ayir", "ko'paytir"]):
        return "calculator"
    if any(w in t for w in ["github", "repo", "loyiha kodi"]):
        return "github"
    if any(w in t for w in ["arxiv", "maqola", "paper", "research paper"]):
        return "arxiv"
    if any(w in t for w in ["dataset", "kaggle", "huggingface"]):
        return "kaggle"
    if any(w in t for w in ["internetdan qidir", "web search", "google qidir", "saytlardan top"]):
        return "web_search"
    if any(w in t for w in ["men haqimda nima bilasan", "xotirangdagi faktlar", "xotirangni ko'rsat"]):
        return "memory_recall"
    return "chat"


def _parse_reminder_time(text: str) -> tuple[datetime | None, str]:
    """Matndan vaqt va vazifa matnini ajratib oladi (Toshkent vaqti)."""
    now_tashkent = datetime.now(tz).replace(tzinfo=None)
    t = text.lower()

    # Daqiqa / Minut
    min_match = re.search(r"(\d+)\s*(?:daqiqa|minut|min)", t)
    if min_match:
        minutes = int(min_match.group(1))
        remind_at = now_tashkent + timedelta(minutes=minutes)
        # Sarlavhadan vaqt so'zlarini tozalash
        clean_title = re.sub(r"\d+\s*(?:daqiqa|minut|min)\w*\s*(?:kn|keyin|so'ng)?", "", text, flags=re.IGNORECASE).strip()
        clean_title = re.sub(r"^(?:menga|men|deb|eslat|xabar yubor|yoz|ayt|ok)\s*", "", clean_title, flags=re.IGNORECASE).strip()
        clean_title = re.sub(r"\s*(?:deb|eslat|xabar yubor|yoz|ayt|ok)$", "", clean_title, flags=re.IGNORECASE).strip()
        return remind_at, clean_title or text

    # Soatdan keyin
    hr_match = re.search(r"(\d+)\s*soat", t)
    if "soatdan" in t or "soat keyin" in t or "soat kn" in t:
        if hr_match:
            hours = int(hr_match.group(1))
            remind_at = now_tashkent + timedelta(hours=hours)
            return remind_at, text

    # Aniq soat (masalan 18:30 yoki soat 18 da)
    time_match = re.search(r"(\d{1,2})[:\.](\d{2})", t)
    if time_match:
        hour, minute = int(time_match.group(1)), int(time_match.group(2))
        base = now_tashkent + timedelta(days=1) if "ertaga" in t else now_tashkent
        remind_at = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if remind_at <= now_tashkent:
            remind_at += timedelta(days=1)
        return remind_at, text

    return None, text


@router.message(F.text)
async def handle_text(message: Message):
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    text = message.text.strip()
    intent = _detect_intent(text)

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    if intent == "reminder":
        remind_at, clean_title = _parse_reminder_time(text)
        if remind_at:
            # Toshkent vaqti bo'yicha bazaga saqlash
            await add_reminder(user.id, clean_title, remind_at)
            t_str = remind_at.strftime("%Y-%m-%d %H:%M")
            await message.answer(
                f"✅ **Eslatma saqlandi!**\n\n"
                f"📌 Vazifa: **{clean_title}**\n"
                f"⏰ Vaqt: **{t_str}** (Toshkent vaqti)\n\n"
                f"💪 _Aniq belgilangan vaqtda xabar beraman!_",
                parse_mode="Markdown",
            )
            return
        else:
            await message.answer(
                "⚠️ Aniq vaqtni aniqlay olmadim. Masalan:\n_\"1 daqiqadan kn darsni eslat\"_\n_\"Ertaga soat 14:30 da X ni eslat\"_",
                parse_mode="Markdown",
            )
            return

    if intent == "calculator":
        expr_match = re.search(r"[\d\s\+\-\*\/\^\(\)\.]+", text)
        if expr_match:
            result = calculate(expr_match.group().strip())
            await message.answer(result, parse_mode="Markdown")
            return

    if intent == "github":
        query = re.sub(r"github|repo|loyiha kodi", "", text, flags=re.IGNORECASE).strip()
        thinking = await message.answer("🔍 GitHub'da qidiryapman...")
        result = await github_search(query or text)
        await safe_reply(message, result, thinking)
        return

    if intent == "arxiv":
        query = re.sub(r"arxiv|maqola|paper|research", "", text, flags=re.IGNORECASE).strip()
        thinking = await message.answer("📰 ArXiv'da maqola qidiryapman...")
        result = await arxiv_search(query or text)
        await safe_reply(message, result, thinking)
        return

    if intent == "kaggle":
        query = re.sub(r"dataset|kaggle|huggingface", "", text, flags=re.IGNORECASE).strip()
        thinking = await message.answer("📊 Dataset qidiryapman...")
        result = await kaggle_search(query or text)
        await safe_reply(message, result, thinking)
        return

    if intent == "web_search":
        query = re.sub(r"internetdan qidir|web search|google qidir|saytlardan top", "", text, flags=re.IGNORECASE).strip()
        thinking = await message.answer("🌐 Internetda jonli qidiryapman...")
        result = await web_search(query or text)
        await safe_reply(message, result, thinking)
        return

    if intent == "memory_recall":
        facts = await memory_manager.recall(user.id)
        if not facts:
            await message.answer("🧠 Hali sizga oid ma'lumot saqlanmagan.")
        else:
            lines = ["🧠 **Siz haqingizda biladiganlarim:**\n"]
            for f in facts:
                lines.append(f"• [{f['category']}] {f['fact']}")
            await message.answer("\n".join(lines), parse_mode="Markdown")
        return

    # --- ASOSIY AI JAVOB ---
    await save_message(user.id, "user", text)
    thinking = await message.answer("⚡ Javob tayyorlanmoqda...")

    live_search_info = ""
    t_lower = text.lower()
    if any(k in t_lower for k in ["2025", "2026", "yangilik", "ob-havo", "kurs", "dollar", "hozirgi", "bugungi"]):
        try:
            live_search_info = await search_and_augment(text)
        except Exception:
            pass

    context = await build_context(user.id, current_query=text)
    if live_search_info:
        context.append({"role": "user", "content": live_search_info})

    response, model_used = await get_ai_response(context)

    await save_message(user.id, "assistant", response)
    await safe_reply(message, response, thinking)

    ml_terms = ["one hot encoding", "dropout", "fine-tuning", "rag", "rlhf", "regularization", "hyperparameter"]
    for term in ml_terms:
        if term in text.lower():
            await memory_manager.remember(user.id, "task", f"Mavzu/Vazifa: {text[:100]}")
            break


@router.message(F.photo)
async def handle_photo(message: Message):
    user = await get_or_create_user(telegram_id=message.from_user.id)
    await message.bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
    thinking = await message.answer("🖼️ Rasmni tahlil qilyapman...")

    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    image_data = file_bytes.read()

    caption = message.caption or "Ushbu rasmni batafsil tahlil qilib ber."
    context = await build_context(user.id, current_query=caption)
    context.append({"role": "user", "content": caption})

    response, _ = await get_ai_response(context, image_data=image_data)
    await safe_reply(message, response, thinking)


@router.message(F.document)
async def handle_document(message: Message):
    user = await get_or_create_user(telegram_id=message.from_user.id)
    doc = message.document
    size_mb = doc.file_size / (1024 * 1024)

    if size_mb > MAX_FILE_SIZE_MB:
        await message.answer(f"❌ Fayl hajmi {size_mb:.1f} MB. Maksimum {MAX_FILE_SIZE_MB} MB.")
        return

    thinking = await message.answer(f"📄 '{doc.file_name}' o'qilmoqda...")
    file = await message.bot.get_file(doc.file_id)
    file_bytes_io = await message.bot.download_file(file.file_path)
    file_bytes = file_bytes_io.read()

    extracted_text = await extract_text_from_file(file_bytes, doc.file_name)
    prompt = f"Quyidagi hujjatni tahlil qilib, asosiy fikrlarni O'zbek tilida xulosala:\n\n{extracted_text[:8000]}"

    context = await build_context(user.id, current_query=prompt)
    context.append({"role": "user", "content": prompt})
    response, _ = await get_ai_response(context)
    await safe_reply(message, f"📄 **{doc.file_name} tahlili:**\n\n{response}", thinking)