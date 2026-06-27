from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable, Union
import asyncio
import time


class ThrottlingMiddleware(BaseMiddleware):
    """
    Simple rate limiting middleware to prevent spam.
    Uses in-memory storage with automatic cleanup.
    """

    def __init__(self, rate_limit: float = 0.5, max_tokens: int = 10):
        """
        :param rate_limit: Minimum time between messages in seconds
        :param max_tokens: Maximum burst tokens (token bucket)
        """
        self.rate_limit = rate_limit
        self.max_tokens = max_tokens
        self._buckets: Dict[int, tuple[float, float]] = {}  # user_id -> (tokens, last_update)
        self._cleanup_task: asyncio.Task | None = None

    async def _cleanup_loop(self):
        """Periodically clean up old buckets."""
        while True:
            await asyncio.sleep(300)  # 5 minutes
            now = time.time()
            expired = [
                uid for uid, (_, last) in self._buckets.items()
                if now - last > 600  # 10 minutes inactive
            ]
            for uid in expired:
                self._buckets.pop(uid, None)

    def _consume_token(self, user_id: int) -> bool:
        """Try to consume a token from user's bucket. Returns True if allowed."""
        now = time.time()
        tokens, last = self._buckets.get(user_id, (self.max_tokens, now))

        # Refill tokens based on time passed
        elapsed = now - last
        tokens = min(self.max_tokens, tokens + elapsed / self.rate_limit)

        if tokens >= 1:
            tokens -= 1
            self._buckets[user_id] = (tokens, now)
            return True

        self._buckets[user_id] = (tokens, now)
        return False

    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        # Start cleanup task on first call
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Get user ID
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        # Skip admins
        from bot.config import settings
        if user_id in settings.admin_ids:
            return await handler(event, data)

        # Check rate limit
        if not self._consume_token(user_id):
            # Rate limited
            if isinstance(event, Message):
                try:
                    await event.answer("⏳ Слишком много сообщений! Подожди немного.", show_alert=False)
                except Exception:
                    pass
            elif isinstance(event, CallbackQuery):
                try:
                    await event.answer("⏳ Слишком быстро! Подожди.", show_alert=True)
                except Exception:
                    pass
            return

        return await handler(event, data)