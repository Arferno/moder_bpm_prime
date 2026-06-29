from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Callable, Dict, Any, Awaitable, Union
import logging

logger = logging.getLogger(__name__)

from bot.database.connection import async_session_maker


class DatabaseMiddleware(BaseMiddleware):
    """Middleware to provide database session to handlers with explicit commit/rollback."""

    def __init__(self, session_maker):
        self.session_maker = session_maker

    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        async with self.session_maker() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                logger.error(f"Database error in middleware: {e}")
                raise