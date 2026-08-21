# services/context_builder.py — LLM uchun optimal kontekst yaratish
from config import MAX_RECENT_MESSAGES
from services import db
from services.memory_manager import memory_manager
from prompts.system_prompt import SYSTEM_PROMPT


async def build_context(user_id: int) -> list[dict]:
    """
    LLM uchun to'liq kontekst yaratish:
    System Prompt + Xotira faktlari + Suhbat xulosasi + Oxirgi xabarlar
    """
    messages = []

    # 1. System Prompt + Shaxsiy xotira
    memory_context = await memory_manager.format_for_context(user_id)
    system_content = SYSTEM_PROMPT
    if memory_context:
        system_content += f"\n\n{memory_context}"

    messages.append({"role": "user", "content": f"[SYSTEM]\n{system_content}"})
    messages.append({"role": "model", "content": "Tushundim. Sizga qanday yordam bera olaman?"})

    # 2. Suhbat xulosasi (eski tarix)
    summary = await db.get_summary(user_id)
    if summary:
        messages.append({"role": "user", "content": f"[Oldingi suhbat xulosasi]\n{summary}"})
        messages.append({"role": "model", "content": "Oldingi suhbatimizni eslab oldim."})

    # 3. Oxirgi N ta xabar
    recent = await db.get_recent_messages(user_id, limit=MAX_RECENT_MESSAGES)
    for msg in recent:
        role = "model" if msg.role == "assistant" else "user"
        messages.append({"role": role, "content": msg.content})

    return messages
