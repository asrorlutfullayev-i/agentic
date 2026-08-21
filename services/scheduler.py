# services/scheduler.py — Tezkor Eslatmalar yuborish servisi (Har 10 soniyada)
import logging
import pytz
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from config import TIMEZONE

log = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone=pytz.timezone(TIMEZONE))
_bot_ref = None


def init_scheduler(bot) -> None:
    global _bot_ref
    _bot_ref = bot
    scheduler.add_job(
        _check_reminders,
        trigger=IntervalTrigger(seconds=10),
        id="reminder_checker",
        replace_existing=True,
    )
    scheduler.start()
    log.info("Scheduler ishga tushdi (har 10 soniyada tekshiradi)")


async def _check_reminders() -> None:
    from services.db import get_all_pending_reminders, mark_reminder_sent
    if not _bot_ref:
        return
    try:
        reminders = await get_all_pending_reminders()
        now = datetime.utcnow()
        for r in reminders:
            if r.remind_at <= now:
                telegram_id = r.user.telegram_id if r.user else None
                if not telegram_id:
                    continue
                try:
                    await _bot_ref.send_message(
                        chat_id=telegram_id,
                        text=(
                            f"⏰ **Eslatma vaqti keldi!**\n\n"
                            f"📌 **{r.title}**\n\n"
                            f"💪 _Rejangizni bajarish vaqti bo'ldi!_"
                        ),
                        parse_mode="Markdown",
                    )
                    await mark_reminder_sent(r.id)
                    log.info(f"Eslatma yuborildi: telegram_id={telegram_id}, id={r.id}")
                except Exception as e:
                    log.error(f"Eslatma yuborishda xato: {e}")
    except Exception as e:
        log.error(f"Reminder checker xatosi: {e}")