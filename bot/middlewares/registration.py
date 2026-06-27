from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Callable, Dict, Any, Awaitable, Union

from bot.database.crud import get_or_create_user


class RegistrationMiddleware(BaseMiddleware):
    """
    Middleware to automatically register users in database
    when they send their first message or press a button.
    """

    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        # Get user from event
        user = None
        chat = None

        if isinstance(event, Message):
            user = event.from_user
            chat = event.chat
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            chat = event.message.chat if event.message else None

        if not user or user.is_bot:
            return await handler(event, data)

        # Get database session
        session: AsyncSession = data.get("session")
        if not session:
            return await handler(event, data)

        # Register or get user
        db_user = await get_or_create_user(
            session,
            tg_id=user.id,
            username=user.username,
            full_name=user.full_name or user.first_name or "Unknown",
        )

        # Add user to data for handlers
        data["db_user"] = db_user

        # If in group, ensure chat is tracked (optional)
        if chat and chat.type in ("group", "supergroup"):
            data["chat_id"] = chat.id
            data["chat_title"] = chat.title

        return await handler(event, data)