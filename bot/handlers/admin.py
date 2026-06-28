from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from bot.database.models import User, ModerationLog, ModerationAction
from bot.database.crud import get_user_by_id, get_all_blacklist_words, invalidate_blacklist_cache
from bot.services.moderation_service import (
    ban_user,
    unban_user,
    mute_user,
    unmute_user,
    warn_user,
    unwarn_user,
)
from bot.filters.is_admin import IsSuperAdminFilter
from bot.config import settings
from bot.utils.formatting import format_money, format_number
from bot.utils.helpers import get_mention


router = Router(name="admin")


class BroadcastState(StatesGroup):
    waiting_text = State()
    waiting_confirm = State()


@router.message(Command("stats"), IsSuperAdminFilter())
async def cmd_stats(message: Message, session: AsyncSession):
    """Bot statistics."""
    # Total users
    total_users = await session.execute(select(func.count(User.id)))
    total_users = total_users.scalar()

    # Active users (last 7 days)
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    active_users = await session.execute(
        select(func.count(User.id)).where(User.updated_at >= week_ago)
    )
    active_users = active_users.scalar()

    # Total money in economy
    total_money = await session.execute(select(func.sum(User.balance)))
    total_money = total_money.scalar() or 0

    # Total exp
    total_exp = await session.execute(select(func.sum(User.exp)))
    total_exp = total_exp.scalar() or 0

    # Banned users
    banned_users = await session.execute(select(func.count(User.id)).where(User.is_banned == True))
    banned_users = banned_users.scalar()

    # Muted users
    muted_users = await session.execute(select(func.count(User.id)).where(User.is_muted == True))
    muted_users = muted_users.scalar()

    # Blacklist words
    bl_count = await session.execute(select(func.count(User.id)).select_from(User.__table__))  # dummy
    bl_words = await get_all_blacklist_words(session)

    # Moderation logs (last 24h)
    day_ago = datetime.utcnow() - timedelta(days=1)
    recent_logs = await session.execute(
        select(func.count(ModerationLog.id)).where(ModerationLog.created_at >= day_ago)
    )
    recent_logs = recent_logs.scalar()

    text = (
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: <b>{total_users}</b>\n"
        f"🟢 Активных (7 дн.): <b>{active_users}</b>\n"
        f"💰 Денег в экономике: <b>{format_money(total_money)}</b> $\n"
        f"⭐ Всего опыта: <b>{format_number(total_exp)}</b> XP\n"
        f"🚫 Забанено: <b>{banned_users}</b>\n"
        f"🔇 В муте: <b>{muted_users}</b>\n"
        f"📝 Слов в ЧС: <b>{len(bl_words)}</b>\n"
        f"📋 Логов за 24ч: <b>{recent_logs}</b>"
    )
    await message.reply(text, parse_mode="HTML")


@router.message(Command("broadcast"), IsSuperAdminFilter())
async def cmd_broadcast(message: Message, state: FSMContext, session: AsyncSession):
    """Start broadcast: /broadcast <text> or reply to message"""
    if message.reply_to_message:
        # Broadcast replied message
        await state.update_data(
            broadcast_text=message.reply_to_message.html_text or message.reply_to_message.text,
            broadcast_entities=message.reply_to_message.entities,
        )
    elif message.text and len(message.text.split(maxsplit=1)) > 1:
        # Broadcast from command
        text = message.text.split(maxsplit=1)[1]
        await state.update_data(broadcast_text=text, broadcast_entities=None)
    else:
        await message.reply(
            "📢 <b>Рассылка</b>\n\n"
            "Ответь на сообщение или напиши:\n"
            "<code>/broadcast Твой текст</code>\n\n"
            "Поддерживается HTML разметка.",
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    text = data.get("broadcast_text", "")

    # Preview
    await message.reply(
        f"📢 <b>Предпросмотр рассылки:</b>\n\n{text}\n\n"
        f"Отправить всем пользователям?",
        reply_markup=InlineKeyboardBuilder()
        .button(text="✅ Отправить", callback_data="broadcast_confirm")
        .button(text="❌ Отмена", callback_data="broadcast_cancel")
        .as_markup(),
        parse_mode="HTML",
    )
    await state.set_state(BroadcastState.waiting_confirm)


@router.callback_query(F.data == "broadcast_confirm", BroadcastState.waiting_confirm)
async def cb_broadcast_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot):
    data = await state.get_data()
    text = data.get("broadcast_text", "")

    # Get all users
    result = await session.execute(select(User.tg_id))
    user_ids = result.scalars().all()

    sent = 0
    failed = 0
    for tg_id in user_ids:
        try:
            await bot.send_message(tg_id, text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
        # Small delay to avoid rate limits
        import asyncio
        await asyncio.sleep(0.05)

    await callback.message.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"✅ Успешно: <b>{sent}</b>\n"
        f"❌ Ошибок: <b>{failed}</b>",
        parse_mode="HTML",
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "broadcast_cancel", BroadcastState.waiting_confirm)
async def cb_broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Рассылка отменена")
    await callback.answer()


@router.message(Command("give"), IsSuperAdminFilter())
async def cmd_give(message: Message, session: AsyncSession, command: CommandObject):
    """Give money/exp: /give @user <money|exp> <amount>"""
    args = command.args.split() if command.args else []

    if len(args) < 3:
        await message.reply("❌ Формат: /give @user <money|exp> <amount>")
        return

    # Get target user (simplified - by ID)
    target_id = args[0]
    if not target_id.isdigit():
        await message.reply("❌ Укажи ID пользователя")
        return

    target_id = int(target_id)
    resource = args[1].lower()
    amount = int(args[2]) if args[2].isdigit() else 0

    if amount <= 0:
        await message.reply("❌ Сумма должна быть больше 0")
        return

    user = await get_user_by_id(session, target_id)
    if not user:
        await message.reply("❌ Пользователь не найден в БД")
        return

    if resource == "money":
        user.balance += amount
        await message.reply(f"✅ Выдано {format_money(amount)}$ пользователю {user.full_name}")
    elif resource == "exp":
        user.exp += amount
        from bot.utils.helpers import check_level_up
        check_level_up(user)
        await message.reply(f"✅ Выдано {amount} XP пользователю {user.full_name}")
    else:
        await message.reply("❌ Ресурс: money или exp")
        return

    await session.flush()


@router.message(Command("setlevel"), IsSuperAdminFilter())
async def cmd_setlevel(message: Message, session: AsyncSession, command: CommandObject):
    """Set user level: /setlevel @user <level>"""
    args = command.args.split() if command.args else []

    if len(args) < 2:
        await message.reply("❌ Формат: /setlevel @user <level>")
        return

    target_id = args[0]
    if not target_id.isdigit():
        await message.reply("❌ Укажи ID пользователя")
        return

    target_id = int(target_id)
    level = int(args[1]) if args[1].isdigit() else 0

    if level < 1 or level > 1000:
        await message.reply("❌ Уровень от 1 до 1000")
        return

    user = await get_user_by_id(session, target_id)
    if not user:
        await message.reply("❌ Пользователь не найден")
        return

    from bot.utils.helpers import get_exp_for_next_level
    user.level = level
    user.exp = get_exp_for_next_level(level)

    await session.flush()
    await message.reply(f"✅ Установлен уровень {level} для {user.full_name}")


@router.message(Command("reload_blacklist"), IsSuperAdminFilter())
async def cmd_reload_blacklist(message: Message, session: AsyncSession):
    """Force reload blacklist cache."""
    await invalidate_blacklist_cache()
    words = await get_all_blacklist_words(session)
    await message.reply(f"✅ Кэш ЧС обновлен. Слов: {len(words)}")


@router.message(Command("userinfo"), IsSuperAdminFilter())
async def cmd_userinfo(message: Message, session: AsyncSession, command: CommandObject):
    """Get user info: /userinfo @user"""
    args = command.args.split() if command.args else []

    if not args:
        await message.reply("❌ Укажи ID пользователя")
        return

    target_id = args[0]
    if not target_id.isdigit():
        await message.reply("❌ Укажи ID пользователя")
        return

    target_id = int(target_id)
    user = await get_user_by_id(session, target_id)
    if not user:
        await message.reply("❌ Пользователь не найден")
        return

    from bot.utils.formatting import format_profile
    await message.reply(format_profile(user), parse_mode="HTML")


@router.message(Command("logs"), IsSuperAdminFilter())
async def cmd_logs(message: Message, session: AsyncSession, command: CommandObject):
    """Show moderation logs: /logs @user [limit]"""
    args = command.args.split() if command.args else []

    if not args:
        await message.reply("❌ Укажи ID пользователя")
        return

    target_id = args[0]
    if not target_id.isdigit():
        await message.reply("❌ Укажи ID пользователя")
        return

    target_id = int(target_id)
    limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else 20

    user = await get_user_by_id(session, target_id)
    if not user:
        await message.reply("❌ Пользователь не найден")
        return

    from bot.database.crud import get_user_moderation_logs
    logs = await get_user_moderation_logs(session, user.id, limit)

    if not logs:
        await message.reply("📭 Логов нет")
        return

    text = f"📋 <b>Логи модерации: {user.full_name}</b>\n\n"
    for log in logs:
        admin_name = log.admin.full_name if log.admin else "Система"
        text += f"• {log.action.value} — {log.reason or 'Без причины'}\n"
        text += f"  Админ: {admin_name} | {log.created_at.strftime('%d.%m %H:%M')}\n\n"

    await message.reply(text, parse_mode="HTML")


# Import for inline keyboards
from aiogram.utils.keyboard import InlineKeyboardBuilder