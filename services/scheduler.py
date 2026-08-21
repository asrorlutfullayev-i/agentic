# services/scheduler.py — Eslatmalar yuborish tizimi
import logging
import pytz
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from config import TIMEZONE

log = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone=pytz.timezone(TIMEZONE))
_bot_ref = None  # Bot instansiyasi


def init_scheduler(bot) -> None:
    """Schedulerni bot bilan ishga tushirish."""
    global _bot_ref
    _bot_ref = bot
    scheduler.add_job(
        _check_reminders,
        trigger=IntervalTrigger(seconds=30),
        id="reminder_checker",
        replace_existing=True,
    )
    scheduler.start()
    log.info("Scheduler ishga tushdi (har 30 sekundda tekshiradi)")


async def _check_reminders() -> None:
    """Vaqti kelgan eslatmalarni yuborish."""
    from services.db import get_all_pending_reminders, mark_reminder_sent
    if not _bot_ref:
        return
    try:
        reminders = await get_all_pending_reminders()
        now = datetime.utcnow()
        for r in reminders:
            if r.remind_at <= now:
                user = r.user
                try:
                    await _bot_ref.send_message(
                        chat_id=user.telegram_id,
                        text=(
                            f"? **Eslatma!**\n\n"
                            f"?? {r.title}\n\n"
                            f"_Bu eslatmani siz o'zingiz belgilagansiz._"
                        ),
                        parse_mode="Markdown",
                    )
                    await mark_reminder_sent(r.id)
                    log.info(f"Eslatma yuborildi: user={user.telegram_id}, id={r.id}")
                except Exception as e:
                    log.error(f"Eslatma yuborishda xato: {e}")
    except Exception as e:
        log.error(f"Reminder checker xatosi: {e}")
