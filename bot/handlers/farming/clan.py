from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from bot.database.crud import (
    get_user_by_id,
    get_clan,
    get_clan_by_tag,
    get_clan_members,
    get_top_clans,
)
from bot.services.farming_service import (
    create_clan,
    join_clan,
    leave_clan,
)
from bot.services.clan_service import get_clan_info, get_clan_top_members
from bot.keyboards.inline import clan_keyboard, clan_manage_keyboard
from bot.utils.formatting import format_money, format_clan_info
from bot.filters.chat_type import GroupFilter


router = Router(name="clan")


@router.message(Command("clan"), GroupFilter())
async def cmd_clan(message: Message, session: AsyncSession, command: CommandObject):
    """Clan main command."""
    user = await get_user_by_id(session, message.from_user.id)
    if not user:
        await message.reply("❌ Ты не зарегистрирован. Напиши /start в группе.")
        return

    args = command.args.split() if command.args else []

    if not args:
        # Show clan info or clan list
        if user.clan_id:
            clan = await get_clan(session, user.clan_id)
            if clan:
                info = await get_clan_info(session, clan.id)
                text = format_clan_info(clan, info["member_count"], is_member=True)
                await message.reply(text, reply_markup=clan_keyboard(clan, True, clan.owner_id == user.id), parse_mode="HTML")
            else:
                await message.reply("❌ Ошибка загрузки клана")
        else:
            # Show top clans
            clans = await get_top_clans(session, "level", 10)
            text = "🏰 <b>Топ кланов:</b>\n\n"
            for i, clan in enumerate(clans, 1):
                text += f"{i}. [{clan.tag}] {clan.name} — Ур. {clan.level} ({clan.balance}$)\n"
            text += "\nСоздай клан: <code>/clan create <название> <тег></code>\nВступи: <code>/clan join <тег></code>"
            await message.reply(text, parse_mode="HTML")
        return

    subcommand = args[0].lower()

    if subcommand == "create":
        if len(args) < 3:
            await message.reply("❌ Формат: /clan create <название> <тег> (тег 2-16 символов)")
            return
        name = args[1]
        tag = args[2]
        if len(tag) < 2 or len(tag) > 16:
            await message.reply("❌ Тег должен быть от 2 до 16 символов")
            return
        success, msg = await create_clan(session, user, name, tag)
        if success:
            await message.reply(msg, parse_mode="HTML")
        else:
            await message.reply(msg)

    elif subcommand == "join":
        if len(args) < 2:
            await message.reply("❌ Формат: /clan join <тег>")
            return
        tag = args[1]
        success, msg = await join_clan(session, user, tag)
        if success:
            clan = await get_clan_by_tag(session, tag)
            if clan:
                await message.reply(msg, reply_markup=clan_keyboard(clan, True, False), parse_mode="HTML")
            else:
                await message.reply(msg)
        else:
            await message.reply(msg)

    elif subcommand == "leave":
        success, msg = await leave_clan(session, user)
        await message.reply(msg)

    elif subcommand == "info":
        if len(args) < 2:
            if user.clan_id:
                clan = await get_clan(session, user.clan_id)
            else:
                await message.reply("❌ Укажи тег клана: /clan info <тег>")
                return
        else:
            clan = await get_clan_by_tag(session, args[1])

        if not clan:
            await message.reply("❌ Клан не найден")
            return

        info = await get_clan_info(session, clan.id)
        text = format_clan_info(clan, info["member_count"], is_member=(user.clan_id == clan.id))
        await message.reply(text, reply_markup=clan_keyboard(clan, user.clan_id == clan.id, clan.owner_id == user.id), parse_mode="HTML")

    elif subcommand == "top":
        clans = await get_top_clans(session, "level", 15)
        text = "🏰 <b>Топ кланов по уровню:</b>\n\n"
        for i, clan in enumerate(clans, 1):
            text += f"{i}. [{clan.tag}] {clan.name} — Ур. {clan.level}, {clan.balance}$\n"
        await message.reply(text, parse_mode="HTML")

    elif subcommand == "members":
        if not user.clan_id:
            await message.reply("❌ Ты не в клане")
            return
        clan = await get_clan(session, user.clan_id)
        members = await get_clan_top_members(session, clan.id, 20)
        text = f"👥 <b>Участники [{clan.tag}] {clan.name}:</b>\n\n"
        for i, member in enumerate(members, 1):
            role_emoji = {"owner": "👑", "officer": "⭐", "member": "👤"}.get(member.role.value, "👤")
            text += f"{i}. {role_emoji} {member.user.full_name} — {member.user.exp} XP\n"
        await message.reply(text, parse_mode="HTML")

    elif subcommand == "treasury":
        if not user.clan_id:
            await message.reply("❌ Ты не в клане")
            return
        clan = await get_clan(session, user.clan_id)
        text = (
            f"💰 <b>Казна клана [{clan.tag}] {clan.name}</b>\n\n"
            f"Баланс: <b>{format_money(clan.balance)}</b> $\n"
            f"Уровень: <b>{clan.level}</b>\n"
            f"Доход/час: <b>~{clan.level * 1000 + 50 * 10}</b> $ (прибл.)"
        )
        await message.reply(text, parse_mode="HTML")

    else:
        await message.reply("❌ Неизвестная команда. Доступно: create, join, leave, info, top, members, treasury")


@router.callback_query(F.data.startswith("clan_join:"))
async def cb_clan_join(callback: CallbackQuery, session: AsyncSession):
    clan_id = int(callback.data.split(":")[1])
    user = await get_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрирован", show_alert=True)
        return

    clan = await get_clan(session, clan_id)
    if not clan:
        await callback.answer("❌ Клан не найден", show_alert=True)
        return

    success, msg = await join_clan(session, user, clan.tag)
    if success:
        await callback.message.edit_text(
            msg,
            reply_markup=clan_keyboard(clan, True, False),
            parse_mode="HTML",
        )
    else:
        await callback.answer(msg, show_alert=True)
    await callback.answer()


@router.callback_query(F.data.startswith("clan_leave:"))
async def cb_clan_leave(callback: CallbackQuery, session: AsyncSession):
    clan_id = int(callback.data.split(":")[1])
    user = await get_user_by_id(session, callback.from_user.id)
    if not user or user.clan_id != clan_id:
        await callback.answer("❌ Ты не в этом клане", show_alert=True)
        return

    success, msg = await leave_clan(session, user)
    if success:
        await callback.message.edit_text(msg, parse_mode="HTML")
    else:
        await callback.answer(msg, show_alert=True)
    await callback.answer()


@router.callback_query(F.data.startswith("clan_info:"))
async def cb_clan_info(callback: CallbackQuery, session: AsyncSession):
    clan_id = int(callback.data.split(":")[1])
    clan = await get_clan(session, clan_id)
    if not clan:
        await callback.answer("❌ Не найдено", show_alert=True)
        return

    user = await get_user_by_id(session, callback.from_user.id)
    info = await get_clan_info(session, clan.id)
    text = format_clan_info(clan, info["member_count"], is_member=(user and user.clan_id == clan.id))
    await callback.message.edit_text(
        text,
        reply_markup=clan_keyboard(clan, user and user.clan_id == clan.id, clan.owner_id == (user.id if user else 0)),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("clan_members:"))
async def cb_clan_members(callback: CallbackQuery, session: AsyncSession):
    clan_id = int(callback.data.split(":")[1])
    clan = await get_clan(session, clan_id)
    if not clan:
        await callback.answer("❌ Не найдено", show_alert=True)
        return

    members = await get_clan_top_members(session, clan.id, 30)
    text = f"👥 <b>Участники [{clan.tag}] {clan.name}:</b>\n\n"
    for i, member in enumerate(members, 1):
        role_emoji = {"owner": "👑", "officer": "⭐", "member": "👤"}.get(member.role.value, "👤")
        text += f"{i}. {role_emoji} {member.user.full_name} — {member.user.exp} XP\n"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data=f"clan_info:{clan.id}")
    builder.button(text="❌ Закрыть", callback_data="clan_close")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("clan_treasury:"))
async def cb_clan_treasury(callback: CallbackQuery, session: AsyncSession):
    clan_id = int(callback.data.split(":")[1])
    clan = await get_clan(session, clan_id)
    if not clan:
        await callback.answer("❌ Не найдено", show_alert=True)
        return

    text = (
        f"💰 <b>Казна клана [{clan.tag}] {clan.name}</b>\n\n"
        f"Баланс: <b>{format_money(clan.balance)}</b> $\n"
        f"Уровень: <b>{clan.level}</b>"
    )
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("clan_manage:"))
async def cb_clan_manage(callback: CallbackQuery, session: AsyncSession):
    clan_id = int(callback.data.split(":")[1])
    clan = await get_clan(session, clan_id)
    user = await get_user_by_id(session, callback.from_user.id)
    if not clan or not user or clan.owner_id != user.id:
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    await callback.message.edit_text(
        f"⚙️ <b>Управление кланом [{clan.tag}] {clan.name}</b>",
        reply_markup=clan_manage_keyboard(clan),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("clan_officers:"))
async def cb_clan_officers(callback: CallbackQuery, session: AsyncSession):
    clan_id = int(callback.data.split(":")[1])
    clan = await get_clan(session, clan_id)
    user = await get_user_by_id(session, callback.from_user.id)
    if not clan or not user or clan.owner_id != user.id:
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    members = await get_clan_members(session, clan.id)
    officers = [m for m in members if m.role.value == "officer"]
    regular = [m for m in members if m.role.value == "member"]

    text = f"⭐ <b>Офицеры клана [{clan.tag}] {clan.name}:</b>\n\n"
    for m in officers:
        text += f"• {m.user.full_name}\n"
    text += "\n👥 <b>Участники:</b>\n"
    for m in regular[:10]:
        text += f"• {m.user.full_name}\n"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data=f"clan_manage:{clan.id}")
    builder.button(text="❌ Закрыть", callback_data="clan_close")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("clan_disband:"))
async def cb_clan_disband(callback: CallbackQuery, session: AsyncSession):
    clan_id = int(callback.data.split(":")[1])
    clan = await get_clan(session, clan_id)
    user = await get_user_by_id(session, callback.from_user.id)
    if not clan or not user or clan.owner_id != user.id:
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    # Ask for confirmation
    from bot.keyboards.inline import confirm_keyboard
    await callback.message.edit_text(
        f"⚠️ <b>Ты точно хочешь распустить клан [{clan.tag}] {clan.name}?</b>\n\n"
        f"Это действие необратимо! Все участники потеряют клан.",
        reply_markup=confirm_keyboard("disband_clan", clan.id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm:disband_clan:"))
async def cb_confirm_disband(callback: CallbackQuery, session: AsyncSession):
    clan_id = int(callback.data.split(":")[2])
    clan = await get_clan(session, clan_id)
    user = await get_user_by_id(session, callback.from_user.id)
    if not clan or not user or clan.owner_id != user.id:
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    from bot.services.clan_service import disband_clan
    await disband_clan(session, clan_id)

    await callback.message.edit_text("✅ Клан распущен.", parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "clan_top")
async def cb_clan_top(callback: CallbackQuery, session: AsyncSession):
    clans = await get_top_clans(session, "level", 15)
    text = "🏰 <b>Топ кланов по уровню:</b>\n\n"
    for i, clan in enumerate(clans, 1):
        text += f"{i}. [{clan.tag}] {clan.name} — Ур. {clan.level}, {clan.balance}$\n"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Закрыть", callback_data="clan_close")
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "clan_close")
async def cb_clan_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()