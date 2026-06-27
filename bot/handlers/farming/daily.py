from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from bot.database.crud import get_user_by_id
from bot.services.farming_service import process_daily_reward
from bot.keyboards.inline import confirm_keyboard
from bot.utils.formatting import format_money, format_time
from bot.filters.chat_type import GroupFilter


router = Router(name="daily")


@router.message(Command("daily"), GroupFilter)
async def cmd_daily(message: Message, session: AsyncSession):
    """Daily reward command."""
    user = await get_user_by_id(session, message.from_user.id)
    if not user:
        await message.reply("❌ Ты не зарегистрирован. Напиши /start в группе.")
        return

    # Check if in jail
    if user.jail_until and user.jail_until > datetime.utcnow():
        await message.reply("⛓ Ты в тюрьме! Не можешь получать ежедневку.")
        return

    money, exp, streak = await process_daily_reward(session, user)

    if money == 0 and exp == 0:
        # Too early
        if user.last_daily:
            from datetime import datetime, timedelta
            next_time = user.last_daily + timedelta(hours=24)
            remaining = next_time - datetime.utcnow()
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await message.reply(f"⏳ Ежедневка уже получена. Следующая через: {hours}ч {minutes}мин")
        else:
            await message.reply("❌ Ошибка при получении ежедневки")
        return

    streak_text = f"\n🔥 Стрик: <b>{streak} дн.</b>" if streak > 1 else ""

    text = (
        f"🎁 <b>Ежедневная награда получена!</b>\n\n"
        f"💰 Деньги: <b>+{format_money(money)}</b>\n"
        f"⭐ Опыт: <b>+{exp}</b>"
        f"{streak_text}\n\n"
        f"💰 Баланс: <b>{format_money(user.balance)}</b>"
    )

    await message.reply(text, parse_mode="HTML")


@router.message(Command("streak"), GroupFilter)
async def cmd_streak(message: Message, session: AsyncSession):
    """Show current streak."""
    user = await get_user_by_id(session, message.from_user.id)
    if not user:
        await message.reply("❌ Ты не зарегистрирован.")
        return

    streak = getattr(user, 'daily_streak', 0)
    if streak == 0:
        await message.reply("😔 У тебя нет стрика. Получи ежедневку командой /daily")
        return

    from bot.config import settings
    max_streak = settings.max_streak_days
    next_bonus = streak + 1 if streak < max_streak else max_streak

    text = (
        f"🔥 <b>Твой стрик: {streak} дн.</b>\n\n"
        f"📅 Макс. стрик: {max_streak} дн.\n"
        f"🎯 Следующий бонус: {next_bonus} дн.\n"
        f"💰 Бонус за стрик: +{streak * 50}$ в день"
    )

    await message.reply(text, parse_mode="HTML")