from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.database.models import User, BlacklistWord, BlacklistAction, ModerationAction
from bot.database.crud import (
    get_user_by_id,
    add_blacklist_word,
    remove_blacklist_word,
    toggle_blacklist_word,
    get_all_blacklist_words,
    add_moderation_log,
    set_user_ban,
    set_user_mute,
    increment_user_warns,
    decrement_user_warns,
)
from bot.services.moderation_service import (
    ban_user,
    unban_user,
    mute_user,
    unmute_user,
    warn_user,
    unwarn_user,
)
from bot.keyboards.inline import (
    blacklist_keyboard,
    blacklist_word_keyboard,
    confirm_keyboard,
)
from bot.filters.is_admin import IsAdminFilter, IsSuperAdminFilter
from bot.filters.chat_type import GroupFilter
from bot.utils.formatting import format_money, format_time
from bot.utils.helpers import get_mention, parse_time_string
from bot.config import settings
from bot.utils.text import normalize_word_for_storage


router = Router(name="moderation")


# ==================== HELPER FUNCTIONS ====================

async def get_target_user(message: Message, session: AsyncSession) -> tuple[User | None, int | None]:
    """Extracts target user from reply or command argument."""
    # From reply
    if message.reply_to_message and message.reply_to_message.from_user:
        target_tg_id = message.reply_to_message.from_user.id
        user = await get_user_by_id(session, target_tg_id)
        return user, target_tg_id

    # From command argument
    if message.text:
        parts = message.text.split()
        if len(parts) > 1:
            arg = parts[1]
            if arg.startswith("@"):
                # Username - would need to resolve
                return None, None
            elif arg.isdigit():
                target_tg_id = int(arg)
                user = await get_user_by_id(session, target_tg_id)
                return user, target_tg_id

    return None, None


# ==================== BAN ====================

@router.message(Command("ban"), GroupFilter, IsAdminFilter())
async def cmd_ban(message: Message, session: AsyncSession, bot: Bot, command: CommandObject):
    """Ban user: /ban @user [time] [reason]"""
    user, target_tg_id = await get_target_user(message, session)
    if not user or not target_tg_id:
        await message.reply("❌ Укажи пользователя (ответом или ID)")
        return

    if target_tg_id in settings.admin_ids:
        await message.reply("❌ Нельзя забанить админа")
        return

    # Parse time and reason
    args = command.args.split() if command.args else []
    duration_sec = None
    reason = "Нарушение правил"

    if args:
        time_str = args[0]
        duration_sec = parse_time_string(time_str)
        if duration_sec is None:
            reason = " ".join(args)
        elif len(args) > 1:
            reason = " ".join(args[1:])

    success = await ban_user(session, bot, message.chat.id, target_tg_id, reason, duration_sec)
    if success:
        await message.reply(f"✅ Пользователь забанен на {format_time(duration_sec) if duration_sec else 'навсегда'}")
    else:
        await message.reply("❌ Ошибка при бане")


@router.message(Command("unban"), GroupFilter, IsAdminFilter())
async def cmd_unban(message: Message, session: AsyncSession, bot: Bot):
    """Unban user: /unban @user"""
    user, target_tg_id = await get_target_user(message, session)
    if not user or not target_tg_id:
        await message.reply("❌ Укажи пользователя (ответом или ID)")
        return

    success = await unban_user(session, bot, message.chat.id, target_tg_id)
    if success:
        await message.reply("✅ Пользователь разбанен")
    else:
        await message.reply("❌ Ошибка при разбане")


# ==================== MUTE ====================

@router.message(Command("mute"), GroupFilter, IsAdminFilter())
async def cmd_mute(message: Message, session: AsyncSession, bot: Bot, command: CommandObject):
    """Mute user: /mute @user <time> [reason]"""
    user, target_tg_id = await get_target_user(message, session)
    if not user or not target_tg_id:
        await message.reply("❌ Укажи пользователя (ответом или ID)")
        return

    if target_tg_id in settings.admin_ids:
        await message.reply("❌ Нельзя замутить админа")
        return

    args = command.args.split() if command.args else []
    if not args:
        await message.reply("❌ Укажи время: /mute @user 10m [причина]")
        return

    duration_sec = parse_time_string(args[0])
    if not duration_sec:
        await message.reply("❌ Неверный формат времени. Примеры: 10m, 1h, 1d")
        return

    reason = " ".join(args[1:]) if len(args) > 1 else "Нарушение правил"

    success = await mute_user(session, bot, message.chat.id, target_tg_id, reason, duration_sec)
    if success:
        await message.reply(f"✅ Пользователь замучен на {format_time(duration_sec)}")
    else:
        await message.reply("❌ Ошибка при муте")


@router.message(Command("unmute"), GroupFilter, IsAdminFilter())
async def cmd_unmute(message: Message, session: AsyncSession, bot: Bot):
    """Unmute user: /unmute @user"""
    user, target_tg_id = await get_target_user(message, session)
    if not user or not target_tg_id:
        await message.reply("❌ Укажи пользователя (ответом или ID)")
        return

    success = await unmute_user(session, bot, message.chat.id, target_tg_id)
    if success:
        await message.reply("✅ Пользователь размучен")
    else:
        await message.reply("❌ Ошибка при размуте")


# ==================== WARN ====================

@router.message(Command("warn"), GroupFilter, IsAdminFilter())
async def cmd_warn(message: Message, session: AsyncSession, bot: Bot, command: CommandObject):
    """Warn user: /warn @user [reason]"""
    user, target_tg_id = await get_target_user(message, session)
    if not user or not target_tg_id:
        await message.reply("❌ Укажи пользователя (ответом или ID)")
        return

    if target_tg_id in settings.admin_ids:
        await message.reply("❌ Нельзя выдать варн админу")
        return

    reason = command.args if command.args else "Нарушение правил"

    warns = await warn_user(session, bot, message.chat.id, target_tg_id, reason)
    if warns:
        await message.reply(f"✅ Выдан варн ({warns}/3)")
    else:
        await message.reply("❌ Ошибка при выдаче варна")


@router.message(Command("unwarn"), GroupFilter, IsAdminFilter())
async def cmd_unwarn(message: Message, session: AsyncSession, bot: Bot):
    """Remove warn: /unwarn @user"""
    user, target_tg_id = await get_target_user(message, session)
    if not user or not target_tg_id:
        await message.reply("❌ Укажи пользователя (ответом или ID)")
        return

    success = await unwarn_user(session, bot, message.chat.id, target_tg_id)
    if success:
        await message.reply("✅ Варн снят")
    else:
        await message.reply("❌ Ошибка или варнов нет")


# ==================== BLACKLIST ====================

@router.message(Command("blacklist"), GroupFilter, IsAdminFilter())
async def cmd_blacklist(message: Message, session: AsyncSession, command: CommandObject):
    """Blacklist management: /blacklist add|del|list|toggle <word> [action] [time]"""
    args = command.args.split() if command.args else []

    if not args:
        # Show menu
        await message.reply(
            "📝 <b>Черный список</b>\n\n"
            "Команды:\n"
            "• <code>/blacklist add <слово> [действие] [время]</code> — добавить\n"
            "• <code>/blacklist del <слово></code> — удалить\n"
            "• <code>/blacklist list</code> — список\n"
            "• <code>/blacklist toggle <слово></code> — вкл/выкл\n\n"
            "Действия: warn (по умолчанию), mute, ban, delete\n"
            "Время: 10m, 1h, 1d (для mute/ban)",
            parse_mode="HTML",
        )
        return

    action = args[0].lower()

    if action == "add":
        if len(args) < 2:
            await message.reply("❌ Укажи слово: /blacklist add <слово> [действие] [время]")
            return

        word = args[1]
        bl_action = BlacklistAction.WARN
        duration = 3600

        if len(args) >= 3:
            try:
                bl_action = BlacklistAction(args[2].lower())
            except ValueError:
                await message.reply("❌ Неверное действие: warn, mute, ban, delete")
                return

        if bl_action in (BlacklistAction.MUTE, BlacklistAction.BAN) and len(args) >= 4:
            duration = parse_time_string(args[3]) or 3600

        normalized = normalize_word_for_storage(word)

        # Check if exists
        existing = await session.execute(
            select(BlacklistWord).where(BlacklistWord.normalized_word == normalized)
        )
        if existing.scalar_one_or_none():
            await message.reply("❌ Такое слово уже в черном списке")
            return

        await add_blacklist_word(
            session,
            word=word,
            normalized_word=normalized,
            action=bl_action,
            duration_sec=duration,
            created_by=message.from_user.id,
        )
        await message.reply(f"✅ Добавлено в ЧС: <b>{word}</b> (действие: {bl_action.value})", parse_mode="HTML")

    elif action == "del":
        if len(args) < 2:
            await message.reply("❌ Укажи слово: /blacklist del <слово>")
            return

        word = args[1]
        success = await remove_blacklist_word(session, word)
        if success:
            await message.reply(f"✅ Удалено из ЧС: <b>{word}</b>", parse_mode="HTML")
        else:
            await message.reply("❌ Слово не найдено")

    elif action == "list":
        words = await get_all_blacklist_words(session)
        if not words:
            await message.reply("📭 Черный список пуст")
            return

        text = "📝 <b>Черный список:</b>\n\n"
        for i, w in enumerate(words, 1):
            status = "🟢" if w.is_active else "🔴"
            text += f"{i}. {status} <code>{w.word}</code> — {w.action.value}"
            if w.action in (BlacklistAction.MUTE, BlacklistAction.BAN):
                text += f" ({format_time(w.duration_sec)})"
            text += "\n"

        await message.reply(text, parse_mode="HTML")

    elif action == "toggle":
        if len(args) < 2:
            await message.reply("❌ Укажи слово: /blacklist toggle <слово>")
            return

        word = args[1]
        bl_word = await toggle_blacklist_word(session, word)
        if bl_word:
            status = "включено" if bl_word.is_active else "выключено"
            await message.reply(f"✅ Слово <b>{word}</b> {status}", parse_mode="HTML")
        else:
            await message.reply("❌ Слово не найдено")

    else:
        await message.reply("❌ Неизвестная команда. Используй: add, del, list, toggle")


# ==================== CALLBACKS FOR BLACKLIST ====================

@router.callback_query(F.data == "bl_add")
async def cb_bl_add(callback: CallbackQuery):
    await callback.message.edit_text(
        "📝 Введи слово для добавления в ЧС:\n"
        "Формат: <code>слово действие время</code>\n"
        "Пример: <code>мат warn</code> или <code>реклама mute 1h</code>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bl_list:"))
async def cb_bl_list(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    words = await get_all_blacklist_words(session)
    per_page = 10
    start = (page - 1) * per_page
    end = start + per_page
    page_words = words[start:end]

    text = f"📝 <b>Черный список (стр. {page}):</b>\n\n"
    for w in page_words:
        status = "🟢" if w.is_active else "🔴"
        text += f"{status} <code>{w.word}</code> — {w.action.value}"
        if w.action in (BlacklistAction.MUTE, BlacklistAction.BAN):
            text += f" ({format_time(w.duration_sec)})"
        text += "\n"

    # Build keyboard with word buttons
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for w in page_words:
        builder.button(text=f"{'🟢' if w.is_active else '🔴'} {w.word}", callback_data=f"bl_word:{w.id}")
    # Pagination
    total_pages = (len(words) + per_page - 1) // per_page
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"bl_list:{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"bl_list:{page+1}"))
    builder.row(*nav)
    builder.button(text="❌ Закрыть", callback_data="bl_close")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("bl_word:"))
async def cb_bl_word(callback: CallbackQuery, session: AsyncSession):
    word_id = int(callback.data.split(":")[1])
    result = await session.execute(select(BlacklistWord).where(BlacklistWord.id == word_id))
    word = result.scalar_one_or_none()
    if not word:
        await callback.answer("❌ Не найдено", show_alert=True)
        return

    text = (
        f"📝 <b>Слово в ЧС:</b>\n\n"
        f"Слово: <code>{word.word}</code>\n"
        f"Нормализованное: <code>{word.normalized_word}</code>\n"
        f"Действие: <b>{word.action.value}</b>\n"
        f"Длительность: <b>{format_time(word.duration_sec)}</b>\n"
        f"Статус: <b>{'Активно' if word.is_active else 'Неактивно'}</b>\n"
        f"Добавлено: <b>{word.created_at.strftime('%d.%m.%Y %H:%M')}</b>"
    )
    await callback.message.edit_text(text, reply_markup=blacklist_word_keyboard(word.id), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("bl_toggle:"))
async def cb_bl_toggle(callback: CallbackQuery, session: AsyncSession):
    word_id = int(callback.data.split(":")[1])
    bl_word = await toggle_blacklist_word(session, word_id)
    if bl_word:
        await callback.answer(f"{'Включено' if bl_word.is_active else 'Выключено'}")
        await cb_bl_word(callback, session)
    else:
        await callback.answer("❌ Не найдено", show_alert=True)


@router.callback_query(F.data.startswith("bl_del:"))
async def cb_bl_del(callback: CallbackQuery, session: AsyncSession):
    word_id = int(callback.data.split(":")[1])
    result = await session.execute(select(BlacklistWord).where(BlacklistWord.id == word_id))
    word = result.scalar_one_or_none()
    if not word:
        await callback.answer("❌ Не найдено", show_alert=True)
        return

    await remove_blacklist_word(session, word.word)
    await callback.answer("✅ Удалено")
    await cb_bl_list(callback, session)


@router.callback_query(F.data == "bl_close")
async def cb_bl_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()