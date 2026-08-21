# middlewares/auth.py — Foydalanuvchi ruxsati tekshiruvi
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from typing import Callable, Any, Awaitable
from config import ALLOWED_USER_IDS


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if ALLOWED_USER_IDS and isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
            if user_id not in ALLOWED_USER_IDS:
                await event.answer(
                    "?? Kechirasiz, bu bot shaxsiy foydalanish uchun mo'ljallangan."
                )
                return
        return await handler(event, data)
