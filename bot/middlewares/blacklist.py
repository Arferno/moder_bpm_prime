from aiogram import BaseMiddleware
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Callable, Dict, Any, Awaitable

from bot.database.crud import get_cached_blacklist
from bot.utils.text import check_blacklist_match
from bot.services.moderation_service import apply_blacklist_action


class BlacklistMiddleware(BaseMiddleware):
    """
    Middleware to check every message against blacklist words.
    Only works in groups/supergroups.
    """

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        # Skip non-text messages
        if not event.text or not event.chat:
            return await handler(event, data)

        # Only process groups and supergroups
        if event.chat.type not in ("group", "supergroup"):
            return await handler(event, data)

        # Skip bots
        if event.from_user and event.from_user.is_bot:
            return await handler(event, data)

        # Skip admins (they can say anything)
        from bot.config import settings
        if event.from_user and event.from_user.id in settings.admin_ids:
            return await handler(event, data)

        session: AsyncSession = data.get("session")
        if not session:
            return await handler(event, data)

        # Get cached blacklist
        blacklist_words = await get_cached_blacklist(session)
        if not blacklist_words:
            return await handler(event, data)

        # Check message
        matched, word = check_blacklist_match(event.text, blacklist_words)
        if not matched or not word:
            return await handler(event, data)

        # Delete the message
        try:
            await event.delete()
        except Exception:
            pass  # No permission to delete

        # Apply action if user exists
        if event.from_user:
            await apply_blacklist_action(
                session=session,
                bot=event.bot,
                chat_id=event.chat.id,
                user_id=event.from_user.id,
                word=word,
                message_text=event.text,
            )

        # Don't continue processing (block other handlers)
        return

        # Note: we don't call handler(event, data) here to block further processing