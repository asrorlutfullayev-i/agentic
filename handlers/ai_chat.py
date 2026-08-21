# handlers/ai_chat.py — Tezkor va xavfsiz AI suhbat handler
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
from services.tools.web_search import web_search
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
    # 4000 belgidan uzun bo'lsa bo'laklash
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)] if len(text) > 4000 else [text]

    for idx, chunk in enumerate(chunks):
        try:
            if idx == 0 and thinking_msg:
                await thinking_msg.edit_text(chunk, parse_mode="Markdown")
            else:
                await message.answer(chunk, parse_mode="Markdown")
        except TelegramBadRequest:
            # Agar Markdown parsing xato bersa oddiy matn sifatida chiqaradi
            if idx == 0 and thinking_msg:
                await thinking_msg.edit_text(chunk, parse_mode=None)
            else:
                await message.answer(chunk, parse_mode=None)


def _detect_intent(text: str) -> str:
    """Matn maqsadini aniqlash."""
    t = text.lower()
    if any(w in t for w in ["eslat", "eslatma", "yodlatir", "reminder", "ertaga", "bugun"]) and any(c.isdigit() for c in t):
        return "reminder"
    if any(w in t for w in ["hisobla", "hisopla", "necha", "qo'sh", "ayir", "ko'paytir"]):
        return "calculator"
    if any(w in t for w in ["github", "repo", "loyiha kodi"]):
        return "github"
    if any(w in t for w in ["arxiv", "maqola", "paper", "research paper"]):
        return "arxiv"
    if any(w in t for w in ["dataset", "kaggle", "huggingface"]):
        return "kaggle"
    if any(w in t for w in ["qidir", "topib ber", "internetdan qidir"]):
        return "web_search"
    if any(w in t for w in ["men haqimda nima bilasan", "xotirangdagi faktlar", "xotirangni ko'rsat"]):
        return "memory_recall"
    return "chat"


async def _parse_reminder_time(text: str) -> datetime | None:
    now = datetime.now(tz)
    t = text.lower()
    time_match = re.search(r"(\d{1,2})[:\.](\d{2})", t)
    hour, minute = (int(time_match.group(1)), int(time_match.group(2))) if time_match else (None, None)

    if "ertaga" in t:
        base = now + timedelta(days=1)
    elif "indinga" in t:
        base = now + timedelta(days=2)
    elif re.search(r"(\d+)\s*daqiqa", t):
        mins = int(re.search(r"(\d+)\s*daqiqa", t).group(1))
        return now + timedelta(minutes=mins)
    elif re.search(r"(\d+)\s*soatdan", t):
        hrs = int(re.search(r"(\d+)\s*soatdan", t).group(1))
        return now + timedelta(hours=hrs)
    else:
        base = now

    if hour is not None:
        remind_at = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if remind_at <= now:
            remind_at += timedelta(days=1)
        return remind_at
    return None


@router.message(F.text)
async def handle_text(message: Message):
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    text = message.text.strip()
    intent = _detect_intent(text)

    # Typing indikatorini yoqish
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    if intent == "reminder":
        remind_at = await _parse_reminder_time(text)
        if remind_at:
            await add_reminder(user.id, text, remind_at.astimezone(pytz.utc).replace(tzinfo=None))
            t_str = remind_at.strftime("%Y-%m-%d %H:%M")
            await message.answer(
                f"✅ Eslatma saqlandi!\n\n📌 **{text}**\n⏰ Vaqt: **{t_str}** ({TIMEZONE})\n\nVaqti kelganda eslataman! 💪",
                parse_mode="Markdown",
            )
            return
        else:
            await message.answer(
                "⚠️ Aniq vaqtni aniqlay olmadim. Masalan:\n_\"Ertaga soat 14:30 da X ni eslat\"_",
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
        query = re.sub(r"qidir|topib ber|internetdan qidir", "", text, flags=re.IGNORECASE).strip()
        thinking = await message.answer("🔎 Internetda qidiryapman...")
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

    # --- ASOSIY AI JAVOB (Tezkor: ~1 soniya) ---
    await save_message(user.id, "user", text)
    thinking = await message.answer("⚡ Javob tayyorlanmoqda...")

    context = await build_context(user.id, current_query=text)
    response, model_used = await get_ai_response(context)

    await save_message(user.id, "assistant", response)
    await safe_reply(message, response, thinking)

    # Qisqa texnik vazifalarni avtomatik xotiraga olish
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