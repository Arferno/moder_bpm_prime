from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from bot.database.crud import get_user_by_id, get_all_crimes, get_available_crimes, get_user_crime_cooldown
from bot.services.farming_service import process_crime
from bot.keyboards.inline import crimes_list_keyboard
from bot.utils.formatting import format_money, format_time, format_crime_info
from bot.filters.chat_type import GroupFilter


router = Router(name="crime")


@router.message(Command("crime"), GroupFilter())
async def cmd_crime(message: Message, session: AsyncSession):
    """Show available crimes."""
    user = await get_user_by_id(session, message.from_user.id)
    if not user:
        await message.reply("❌ Ты не зарегистрирован. Напиши /start в группе.")
        return

    # Check if in jail
    if user.jail_until and user.jail_until > datetime.utcnow():
        from bot.utils.helpers import format_time_remaining
        remaining = format_time_remaining(user.jail_until)
        await message.reply(f"⛓ Ты в тюрьме! Осталось: {remaining}")
        return

    crimes = await get_available_crimes(session, user.level)
    if not crimes:
        await message.reply("😔 Нет доступных преступлений для твоего уровня.")
        return

    text = (
        f"🔫 <b>Преступный мир</b>\n\n"
        f"Твой уровень: <b>{user.level}</b>\n"
        f"⚠️ Риск: можешь попасть в тюрьму!\n\n"
        f"Выбери преступление:"
    )
    await message.reply(text, reply_markup=crimes_list_keyboard(crimes), parse_mode="HTML")


@router.callback_query(F.data.startswith("crime_select:"))
async def cb_crime_select(callback: CallbackQuery, session: AsyncSession):
    """Handle crime selection."""
    crime_id = int(callback.data.split(":")[1])
    user = await get_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрирован", show_alert=True)
        return

    success, msg, money, exp, jail_time = await process_crime(session, user, crime_id)

    if success:
        if jail_time:
            text = (
                f"🎉 <b>Успешно! Но тебя заметили...</b>\n\n"
                f"💰 +{format_money(money)}$\n"
                f"⭐ +{exp} XP\n"
                f"🏢 Тюрьма на {format_time(jail_time)}"
            )
        else:
            text = (
                f"🎉 <b>Успешно!</b>\n\n"
                f"💰 +{format_money(money)}$\n"
                f"⭐ +{exp} XP"
            )
    else:
        text = f"🚫 <b>Неудача!</b>\n\n{msg}"

    text += f"\n\n💰 Баланс: {format_money(user.balance)}$\n⭐ Опыт: {user.exp} XP"

    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "crime_cancel")
async def cb_crime_cancel(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.message(Command("crimeinfo"), GroupFilter())
async def cmd_crimeinfo(message: Message, session: AsyncSession, command: CommandObject):
    """Show crime info: /crimeinfo <crime_id>"""
    if not command.args or not command.args.isdigit():
        await message.reply("❌ Укажи ID преступления: /crimeinfo <id>")
        return

    from bot.database.crud import get_crime
    crime = await get_crime(session, int(command.args))
    if not crime:
        await message.reply("❌ Преступление не найдено")
        return

    await message.reply(format_crime_info(crime), parse_mode="HTML")