# middlewares/rate_limit.py — Spam himoyasi
import time
from collections import defaultdict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from typing import Callable, Any, Awaitable
from config import RATE_LIMIT_MESSAGES, RATE_LIMIT_WINDOW

_user_requests: dict[int, list[float]] = defaultdict(list)


class RateLimitMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            uid = event.from_user.id
            now = time.time()
            _user_requests[uid] = [t for t in _user_requests[uid] if now - t < RATE_LIMIT_WINDOW]
            if len(_user_requests[uid]) >= RATE_LIMIT_MESSAGES:
                await event.answer("?? Juda tez yozyapsiz! Iltimos, biroz kuting.")
                return
            _user_requests[uid].append(now)
        return await handler(event, data)
