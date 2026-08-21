# handlers/ai_chat.py — Asosiy AI suhbat, rasm, fayl, ovoz va search handler
import re
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message
from services.db import get_or_create_user, save_message, add_reminder
from services.ai_engine import get_ai_response
from services.context_builder import build_context
from services.memory_manager import memory_manager
from services.tools.web_search import web_search, image_search
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


def _detect_intent(text: str) -> str:
    """Matn maqsadini aniqlash."""
    t = text.lower()
    if any(w in t for w in ["eslat", "eslatma", "yodlatir", "reminder", "soat", "ertaga", "bugun"]):
        if any(c.isdigit() for c in t):
            return "reminder"
    if any(w in t for w in ["hisob", "hisopla", "necha", "qo'sh", "ayir", "ko'payt", "bo'l"]):
        return "calculator"
    if any(w in t for w in ["github", "repo", "loyiha kodi"]):
        return "github"
    if any(w in t for w in ["arxiv", "maqola", "paper", "research"]):
        return "arxiv"
    if any(w in t for w in ["dataset", "kaggle", "huggingface", "ma'lumotlar to'plami"]):
        return "kaggle"
    if any(w in t for w in ["qidir", "topib ber", "internet", "web", "yangilik", "nima bu"]):
        return "web_search"
    if any(w in t for w in ["xotirimda", "eslab qol", "yodimda", "saqla", "bilasanmi meni"]):
        return "memory_save"
    if any(w in t for w in ["nima bilasan", "haqimda", "xotirang", "esingda", "faktlar"]):
        return "memory_recall"
    return "chat"


async def _parse_reminder_time(text: str) -> datetime | None:
    """Matndan vaqtni aniqlash."""
    now = datetime.now(tz)
    t = text.lower()

    # "soat HH:MM" yoki "HH:MM da"
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

    # --- REMINDER ---
    if intent == "reminder":
        remind_at = await _parse_reminder_time(text)
        if remind_at:
            r = await add_reminder(user.id, text, remind_at.astimezone(pytz.utc).replace(tzinfo=None))
            t_str = remind_at.strftime("%Y-%m-%d %H:%M")
            await message.answer(
                f"? Eslatma saqlandi!\n\n"
                f"?? **{text}**\n"
                f"? Vaqt: **{t_str}** ({TIMEZONE})\n\n"
                f"Zo'r qadam! Vaqti kelganda xabar beraman. ??",
                parse_mode="Markdown",
            )
            return
        else:
            await message.answer(
                "?? Aniq vaqtni topa olmadim. Iltimos, shunday yozing:\n"
                "_\"Ertaga soat 14:30 da menga X ni eslat\"_",
                parse_mode="Markdown",
            )
            return

    # --- CALCULATOR ---
    if intent == "calculator":
        expr_match = re.search(r"[\d\s\+\-\*\/\^\(\)\.]+", text)
        if expr_match:
            result = calculate(expr_match.group().strip())
            await message.answer(result, parse_mode="Markdown")
            return

    # --- GITHUB SEARCH ---
    if intent == "github":
        query = re.sub(r"github|repo|loyiha kodi", "", text, flags=re.IGNORECASE).strip()
        thinking = await message.answer("?? GitHub'da qidiryapman...")
        result = await github_search(query or text)
        await thinking.edit_text(result, parse_mode="Markdown")
        return

    # --- ARXIV SEARCH ---
    if intent == "arxiv":
        query = re.sub(r"arxiv|maqola|paper|research", "", text, flags=re.IGNORECASE).strip()
        thinking = await message.answer("?? ArXiv'da maqola qidiryapman...")
        result = await arxiv_search(query or text)
        await thinking.edit_text(result, parse_mode="Markdown")
        return

    # --- DATASET SEARCH ---
    if intent == "kaggle":
        query = re.sub(r"dataset|kaggle|huggingface|ma'lumotlar to'plami", "", text, flags=re.IGNORECASE).strip()
        thinking = await message.answer("?? Dataset qidiryapman...")
        result = await kaggle_search(query or text)
        await thinking.edit_text(result, parse_mode="Markdown")
        return

    # --- WEB SEARCH ---
    if intent == "web_search":
        query = re.sub(r"qidir|topib ber|internet|web|yangilik", "", text, flags=re.IGNORECASE).strip()
        thinking = await message.answer("?? Internetda qidiryapman...")
        result = await web_search(query or text)
        await thinking.edit_text(result, parse_mode="Markdown")
        return

    # --- MEMORY RECALL ---
    if intent == "memory_recall":
        facts = await memory_manager.recall(user.id)
        if not facts:
            await message.answer("?? Hali sizga oid ma'lumot yo'q. Muhim narsalarni aytib qo'ying!")
        else:
            lines = ["?? **Sizga oid eslab qolgan ma'lumotlarim:**\n"]
            for f in facts:
                lines.append(f"• [{f['category']}] {f['fact']}")
            await message.answer("\n".join(lines), parse_mode="Markdown")
        return

    # --- AI CHAT (barcha boshqa holatlar) ---
    await save_message(user.id, "user", text)
    thinking = await message.answer("?? O'ylamoqda...")

    context = await build_context(user.id)
    response, model_used = await get_ai_response(context)

    await save_message(user.id, "assistant", response)
    await thinking.edit_text(response, parse_mode="Markdown")

    # ML/DS vazifalarni avtomatik xotiraga saqlash
    ml_terms = [
        "one hot encoding", "dropout", "fine-tuning", "rag", "rlhf", "backpropagation",
        "gradient descent", "overfitting", "regularization", "hyperparameter",
        "cross validation", "confusion matrix", "embedding", "attention", "transformer"
    ]
    text_lower = text.lower()
    for term in ml_terms:
        if term in text_lower:
            await memory_manager.remember(user.id, "task", f"ML/DS vazifa: {text[:100]}")
            break


@router.message(F.photo)
async def handle_photo(message: Message):
    user = await get_or_create_user(telegram_id=message.from_user.id)
    thinking = await message.answer("??? Rasmni tahlil qilyapman...")

    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    image_data = file_bytes.read()

    caption = message.caption or "Bu rasmda nima bor? Batafsil tushuntir."
    context = await build_context(user.id)
    context.append({"role": "user", "content": caption})

    response, _ = await get_ai_response(context, image_data=image_data)
    await thinking.edit_text(response, parse_mode="Markdown")


@router.message(F.document)
async def handle_document(message: Message):
    user = await get_or_create_user(telegram_id=message.from_user.id)
    doc = message.document
    size_mb = doc.file_size / (1024 * 1024)

    if size_mb > MAX_FILE_SIZE_MB:
        await message.answer(f"? Fayl hajmi {size_mb:.1f} MB. Maksimum {MAX_FILE_SIZE_MB} MB.")
        return

    thinking = await message.answer(f"?? '{doc.file_name}' faylini o'qimoqda...")
    file = await message.bot.get_file(doc.file_id)
    file_bytes_io = await message.bot.download_file(file.file_path)
    file_bytes = file_bytes_io.read()

    extracted_text = await extract_text_from_file(file_bytes, doc.file_name)
    prompt = f"Quyidagi hujjatni tahlil qilib, asosiy fikrlarni va muhim ma'lumotlarni O'zbek tilida xulosala:\n\n{extracted_text[:8000]}"

    context = await build_context(user.id)
    context.append({"role": "user", "content": prompt})
    response, _ = await get_ai_response(context)
    await thinking.edit_text(f"?? **{doc.file_name} tahlili:**\n\n{response}", parse_mode="Markdown")


@router.message(F.voice)
async def handle_voice(message: Message):
    await message.answer(
        "??? Ovozli xabaringizni oldim!\n\n"
        "_(Hozirda ovozni matnga o'girish funksiyasi keyingi yangilanishda qo'shiladi. "
        "Iltimos, matn orqali yuboring.)_",
        parse_mode="Markdown",
    )
