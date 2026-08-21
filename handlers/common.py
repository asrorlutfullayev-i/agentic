# handlers/common.py — /start, /help, /memory, /tasks, /clear
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from services.db import get_or_create_user, get_pending_reminders, clear_history
from services.memory_manager import memory_manager

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    name = message.from_user.first_name or "do'stim"
    await message.answer(
        f"Salom, **{name}**! ??\n\n"
        f"Men sizning shaxsiy AI yordamchingizman — 6 sohada senior mutaxassis.\n\n"
        f"?? *Nima qila olaman:*\n"
        f"• Har qanday texnik va biznes savollaringizga javob beraman\n"
        f"• Vazifalaringizni saqlyman va eslatib turaman\n"
        f"• Rasm, PDF va ovozli xabarlar bilan ishlayman\n"
        f"• Web, GitHub, dataset va maqola qidiraman\n\n"
        f"Boshlaylikmi? Nima kerak? ??",
        parse_mode="Markdown",
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "?? **Qo'llanma:**\n\n"
        "• Matn yozing — javob beraman\n"
        "• Rasm yuboring — tahlil qilaman\n"
        "• PDF/DOCX/TXT yuboring — o'qib xulosalayman\n"
        "• Ovozli xabar yuboring — tushunaman\n\n"
        "?? **Eslatma qo'shish:**\n"
        "_\"Ertaga soat 10da darsim bor, eslat\"_ deb yozing\n\n"
        "?? **Buyruqlar:**\n"
        "/tasks — Eslatmalarimni ko'rish\n"
        "/memory — Mening xotiramni ko'rish\n"
        "/clear — Suhbat tarixini tozalash\n"
        "/help — Yordam",
        parse_mode="Markdown",
    )


@router.message(Command("memory"))
async def cmd_memory(message: Message):
    user = await get_or_create_user(telegram_id=message.from_user.id)
    facts = await memory_manager.recall(user.id)
    if not facts:
        await message.answer("?? Xotiram hozircha bo'sh. Muhim narsalarni aytsangiz, eslab qolaman!")
        return
    lines = ["?? **Mening xotiram (siz haqingizda biladiganlarim):**\n"]
    for f in facts:
        lines.append(f"• [{f['category']}] {f['fact']} _(#{f['id']})_")
    lines.append(f"\n_Biror faktni o'chirish uchun: \"#{'{id}'}ni o'chir\" deb yozing_")
    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(Command("tasks"))
async def cmd_tasks(message: Message):
    user = await get_or_create_user(telegram_id=message.from_user.id)
    reminders = await get_pending_reminders(user.id)
    if not reminders:
        await message.answer("?? Hozircha kutilayotgan eslatmalaringiz yo'q.")
        return
    lines = ["?? **Kutilayotgan eslatmalaringiz:**\n"]
    for r in reminders:
        t = r.remind_at.strftime("%Y-%m-%d %H:%M")
        lines.append(f"• _{t}_ — {r.title} _(#{r.id})_")
    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(Command("clear"))
async def cmd_clear(message: Message):
    user = await get_or_create_user(telegram_id=message.from_user.id)
    await clear_history(user.id)
    await message.answer("??? Suhbat tarixingiz tozalandi. Yangi suhbat boshladik!")
