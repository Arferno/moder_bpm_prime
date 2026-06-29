from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable, Union
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """
    Rate limiting middleware to prevent spam.
    Currently disabled (always allows) to prevent issues.
    """

    def __init__(self, rate_limit: float = 0.0, max_tokens: int = 1000):
        self.rate_limit = rate_limit
        self.max_tokens = max_tokens
        self._buckets: Dict[int, tuple[float, float]] = {}
        self._cleanup_task: asyncio.Task | None = None

    async def _cleanup_loop(self):
        while True:
            try:
                await asyncio.sleep(300)
                now = time.time()
                expired = [
                    uid for uid, (_, last) in self._buckets.items()
                    if now - last > 600
                ]
                for uid in expired:
                    self._buckets.pop(uid, None)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Throttle cleanup error: {e}")
                await asyncio.sleep(60)

    def _consume_token(self, user_id: int) -> bool:
        """Always allow - throttling disabled."""
        return True

    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        # Skip admins completely
        from bot.config import settings
        if user_id in settings.admin_ids:
            return await handler(event, data)

        return await handler(event, data)