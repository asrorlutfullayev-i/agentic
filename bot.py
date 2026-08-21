# ============================================================
#  bot.py — Asosiy kirish nuqtasi (Entry Point)
# ============================================================
import asyncio
import logging
import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, LOG_LEVEL, validate_config
from services.db import init_db
from services.scheduler import init_scheduler
from middlewares.auth import AuthMiddleware
from middlewares.rate_limit import RateLimitMiddleware
from handlers import common, ai_chat

# --- Logging sozlash ---
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


async def main() -> None:
    # Konfiguratsiyani tekshirish
    validate_config()
    log.info("Konfiguratsiya tekshirildi. Bot ishga tushmoqda...")

    # Ma'lumotlar bazasini ishga tushirish
    await init_db()
    log.info("Ma'lumotlar bazasi tayyor.")

    # Bot va Dispatcher
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()

    # Middlewares (tartib muhim: avval auth, keyin rate limit)
    dp.message.middleware(AuthMiddleware())
    dp.message.middleware(RateLimitMiddleware())

    # Handlerlarni ro'yxatdan o'tkazish
    dp.include_router(common.router)
    dp.include_router(ai_chat.router)

    # Eslatmalar schedulerini ishga tushirish
    init_scheduler(bot)
    log.info("Scheduler ishga tushdi.")

    # Polling boshlash
    log.info("Bot polling boshlandi. Telegram xabarlarini kutmoqda...")
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await bot.session.close()
        log.info("Bot to'xtatildi.")


if __name__ == "__main__":
    asyncio.run(main())
