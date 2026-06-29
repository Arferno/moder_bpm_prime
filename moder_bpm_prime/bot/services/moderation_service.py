from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot

from bot.database.models import User, BlacklistWord, ModerationLog, ModerationAction, BlacklistAction
from bot.database.crud import (
    add_moderation_log,
    set_user_ban,
    set_user_mute,
    set_user_jail,
    increment_user_warns,
    decrement_user_warns,
    get_user_by_id,
)
from bot.config import settings
from bot.utils.formatting import format_time
from bot.utils.helpers import get_mention


async def apply_blacklist_action(
    session: AsyncSession,
    bot: Bot,
    chat_id: int,
    user_id: int,
    word: BlacklistWord,
    message_text: str,
) -> None:
    """
    Applies the action configured for a blacklist word.
    """
    user = await get_user_by_id(session, user_id)
    if not user:
        return

    # Skip if user is admin
    if user_id in settings.admin_ids:
        return

    action = word.action
    duration = word.duration_sec

    if action == BlacklistAction.DELETE:
        # Message already deleted in middleware
        pass

    elif action == BlacklistAction.WARN:
        await warn_user(session, bot, chat_id, user_id, f"Запрещенное слово: {word.word}", duration)

    elif action == BlacklistAction.MUTE:
        await mute_user(session, bot, chat_id, user_id, f"Запрещенное слово: {word.word}", duration)

    elif action == BlacklistAction.BAN:
        await ban_user(session, bot, chat_id, user_id, f"Запрещенное слово: {word.word}", duration)


async def ban_user(
    session: AsyncSession,
    bot: Bot,
    chat_id: int,
    user_id: int,
    reason: str,
    duration_sec: Optional[int] = None,
    admin_id: Optional[int] = None,
) -> bool:
    """Bans user from chat."""
    user = await get_user_by_id(session, user_id)
    if not user:
        return False

    if user_id in settings.admin_ids:
        return False

    try:
        if duration_sec:
            until_date = datetime.utcnow() + timedelta(seconds=duration_sec)
            await bot.ban_chat_member(chat_id, user_id, until_date=until_date)
        else:
            await bot.ban_chat_member(chat_id, user_id)

        user.is_banned = True
        await add_moderation_log(
            session,
            user_id=user.id,
            action=ModerationAction.BAN,
            admin_id=admin_id,
            reason=reason,
            duration_sec=duration_sec,
        )
        await session.flush()

        # Notify
        try:
            await bot.send_message(
                chat_id,
                f"🚫 {get_mention(user_id, user.full_name)} забанен.\nПричина: {reason}",
                parse_mode="HTML",
            )
        except Exception:
            pass

        return True
    except Exception as e:
        return False


async def unban_user(
    session: AsyncSession,
    bot: Bot,
    chat_id: int,
    user_id: int,
    admin_id: Optional[int] = None,
) -> bool:
    """Unbans user from chat."""
    user = await get_user_by_id(session, user_id)
    if not user:
        return False

    try:
        await bot.unban_chat_member(chat_id, user_id)
        user.is_banned = False
        await add_moderation_log(
            session,
            user_id=user.id,
            action=ModerationAction.UNBAN,
            admin_id=admin_id,
            reason="Разбанен администратором",
        )
        await session.flush()

        try:
            await bot.send_message(
                chat_id,
                f"✅ {get_mention(user_id, user.full_name)} разбанен.",
                parse_mode="HTML",
            )
        except Exception:
            pass

        return True
    except Exception:
        return False


async def mute_user(
    session: AsyncSession,
    bot: Bot,
    chat_id: int,
    user_id: int,
    reason: str,
    duration_sec: int,
    admin_id: Optional[int] = None,
) -> bool:
    """Mutes user in chat."""
    user = await get_user_by_id(session, user_id)
    if not user:
        return False

    if user_id in settings.admin_ids:
        return False

    try:
        until_date = datetime.utcnow() + timedelta(seconds=duration_sec)
        await bot.restrict_chat_member(
            chat_id,
            user_id,
            permissions=None,  # Default restricted permissions (no messages)
            until_date=until_date,
        )

        user.is_muted = True
        user.mute_until = until_date

        await add_moderation_log(
            session,
            user_id=user.id,
            action=ModerationAction.MUTE,
            admin_id=admin_id,
            reason=reason,
            duration_sec=duration_sec,
        )
        await session.flush()

        try:
            await bot.send_message(
                chat_id,
                f"🔇 {get_mention(user_id, user.full_name)} замучен на {format_time(duration_sec)}.\nПричина: {reason}",
                parse_mode="HTML",
            )
        except Exception:
            pass

        return True
    except Exception:
        return False


async def unmute_user(
    session: AsyncSession,
    bot: Bot,
    chat_id: int,
    user_id: int,
    admin_id: Optional[int] = None,
) -> bool:
    """Unmutes user in chat."""
    user = await get_user_by_id(session, user_id)
    if not user:
        return False

    try:
        # Reset permissions to default (allow all)
        from aiogram.types import ChatPermissions
        await bot.restrict_chat_member(
            chat_id,
            user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )

        user.is_muted = False
        user.mute_until = None

        await add_moderation_log(
            session,
            user_id=user.id,
            action=ModerationAction.UNMUTE,
            admin_id=admin_id,
            reason="Размучен администратором",
        )
        await session.flush()

        try:
            await bot.send_message(
                chat_id,
                f"🔊 {get_mention(user_id, user.full_name)} размучен.",
                parse_mode="HTML",
            )
        except Exception:
            pass

        return True
    except Exception:
        return False


async def warn_user(
    session: AsyncSession,
    bot: Bot,
    chat_id: int,
    user_id: int,
    reason: str,
    duration_sec: Optional[int] = None,
    admin_id: Optional[int] = None,
) -> int:
    """Warns user. 3 warns = auto ban."""
    user = await get_user_by_id(session, user_id)
    if not user:
        return 0

    if user_id in settings.admin_ids:
        return 0

    warns = await increment_user_warns(session, user_id)

    await add_moderation_log(
        session,
        user_id=user.id,
        action=ModerationAction.WARN,
        admin_id=admin_id,
        reason=reason,
        duration_sec=duration_sec,
    )
    await session.flush()

    try:
        await bot.send_message(
            chat_id,
            f"⚠️ {get_mention(user_id, user.full_name)} получил предупреждение ({warns}/3).\nПричина: {reason}",
            parse_mode="HTML",
        )
    except Exception:
        pass

    # Auto-ban on 3 warns
    if warns >= 3:
        await ban_user(session, bot, chat_id, user_id, "3 предупреждения", admin_id=admin_id)

    return warns


async def unwarn_user(
    session: AsyncSession,
    bot: Bot,
    chat_id: int,
    user_id: int,
    admin_id: Optional[int] = None,
) -> bool:
    """Removes one warn from user."""
    user = await get_user_by_id(session, user_id)
    if not user or user.warns <= 0:
        return False

    warns = await decrement_user_warns(session, user_id)

    await add_moderation_log(
        session,
        user_id=user.id,
        action=ModerationAction.UNWARN,
        admin_id=admin_id,
        reason="Предупреждение снято администратором",
    )
    await session.flush()

    try:
        await bot.send_message(
            chat_id,
            f"✅ У {get_mention(user_id, user.full_name)} снято предупреждение. Осталось: {warns}/3",
            parse_mode="HTML",
        )
    except Exception:
        pass

    return True


async def check_and_unmute_expired(session: AsyncSession, bot: Bot) -> int:
    """Checks and unmutes users with expired mutes. Returns count unmuted."""
    from sqlalchemy import select
    from bot.database.connection import async_session_maker

    async with async_session_maker() as session:
        now = datetime.utcnow()
        result = await session.execute(
            select(User).where(
                User.is_muted == True,
                User.mute_until != None,
                User.mute_until <= now,
            )
        )
        users = result.scalars().all()

        count = 0
        for user in users:
            try:
                # We need a chat_id - in practice, you'd track which chat they're muted in
                # For now, just clear the mute flag
                user.is_muted = False
                user.mute_until = None
                count += 1
            except Exception:
                pass

        await session.flush()
        return count