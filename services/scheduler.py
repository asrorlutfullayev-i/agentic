# services/scheduler.py — 100% Ishonchli Native Asyncio Taymer (Tashkent Vaqti)
import asyncio
import logging
from datetime import datetime
import pytz
from config import TIMEZONE
from services.db import get_all_pending_reminders, mark_reminder_sent

log = logging.getLogger(__name__)
tz = pytz.timezone(TIMEZONE)


async def check_and_send_reminders(bot) -> None:
    """Toshkent vaqti bo'yicha to'g'ridan-to'g'ri solishtirish va yuborish."""
    now_tashkent = datetime.now(tz).replace(tzinfo=None)
    reminders = await get_all_pending_reminders()

    for r in reminders:
        # Agar belgilangan vaqt yetgan yoki o'tgan bo'lsa
        if r.remind_at <= now_tashkent:
            telegram_id = r.user.telegram_id if r.user else None
            if not telegram_id:
                log.warning(f"Reminder #{r.id} user topilmadi.")
                continue

            try:
                await bot.send_message(
                    chat_id=telegram_id,
                    text=(
                        f"⏰ **Eslatma vaqti keldi!**\n\n"
                        f"📌 **{r.title}**\n\n"
                        f"💪 _Belgilangan rejangizni bajarish vaqti bo'ldi!_"
                    ),
                    parse_mode="Markdown",
                )
                await mark_reminder_sent(r.id)
                log.info(f"✅ Eslatma yuborildi: user={telegram_id}, id={r.id}, title='{r.title}'")
            except Exception as e:
                log.error(f"❌ Eslatma yuborishda xato (#{r.id}): {e}")


async def start_reminder_worker(bot) -> None:
    """Fonda har 5 soniyada to'xtovsiz tekshiruvchi asosiy loop."""
    log.info(f"🚀 Native Eslatmalar Taymeri ishga tushdi ({TIMEZONE} vaqti, har 5 sek).")
    while True:
        try:
            await check_and_send_reminders(bot)
        except Exception as e:
            log.error(f"Reminder worker xatosi: {e}")
        await asyncio.sleep(5)