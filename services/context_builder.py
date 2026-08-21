# services/context_builder.py — LLM uchun optimal kontekst yaratish
from config import MAX_RECENT_MESSAGES
from services import db
from services.memory_manager import memory_manager
from prompts.system_prompt import get_dynamic_system_prompt


async def build_context(user_id: int, current_query: str = "") -> list[dict]:
    """
    LLM uchun to'liq kontekst yaratish:
    Dynamic System Prompt + Xotira faktlari + Suhbat xulosasi + Oxirgi xabarlar
    """
    messages = []

    # 1. Savolga moslashtirilgan yengil va tezkor System Prompt
    system_content = get_dynamic_system_prompt(current_query)
    memory_context = await memory_manager.format_for_context(user_id)
    if memory_context:
        system_content += f"\n\n{memory_context}"

    messages.append({"role": "user", "content": f"[SYSTEM]\n{system_content}"})
    messages.append({"role": "model", "content": "Tushundim. Qanday yordam bera olaman?"})

    # 2. Suhbat xulosasi (agar bor bo'lsa)
    summary = await db.get_summary(user_id)
    if summary:
        messages.append({"role": "user", "content": f"[Oldingi suhbat xulosasi]\n{summary}"})
        messages.append({"role": "model", "content": "Oldingi suhbatimizni esladim."})

    # 3. Oxirgi xabarlar
    recent = await db.get_recent_messages(user_id, limit=MAX_RECENT_MESSAGES)
    for msg in recent:
        role = "model" if msg.role == "assistant" else "user"
        messages.append({"role": role, "content": msg.content})

    return messages