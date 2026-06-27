from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.crud import get_user_by_id, get_top_users
from bot.keyboards.inline import pagination_keyboard
from bot.utils.formatting import format_profile, format_money, format_number
from bot.filters.chat_type import GroupFilter
from bot.services.farming_service import get_level_progress


router = Router(name="profile")


@router.message(Command("profile"), GroupFilter)
async def cmd_profile(message: Message, session: AsyncSession):
    """Show user profile."""
    user = await get_user_by_id(session, message.from_user.id)
    if not user:
        await message.reply("❌ Ты не зарегистрирован. Напиши /start в группе.")
        return

    await message.reply(format_profile(user), parse_mode="HTML")


@router.message(Command("balance"), GroupFilter)
async def cmd_balance(message: Message, session: AsyncSession):
    """Show user balance."""
    user = await get_user_by_id(session, message.from_user.id)
    if not user:
        await message.reply("❌ Ты не зарегистрирован.")
        return

    await message.reply(f"💰 <b>Баланс: {format_money(user.balance)}</b> $", parse_mode="HTML")


@router.message(Command("top"), GroupFilter)
async def cmd_top(message: Message, session: AsyncSession, command: CommandObject):
    """Show leaderboards: /top [money|level|clan]"""
    args = command.args.split() if command.args else []
    by = args[0].lower() if args else "money"

    if by not in ("money", "level", "exp"):
        by = "money"

    users = await get_top_users(session, by=by, limit=20)

    if not users:
        await message.reply("😔 Пока нет участников.")
        return

    title_map = {"money": "Богатейшие", "level": "По уровню", "exp": "По опыту"}
    emoji_map = {"money": "💰", "level": "⭐", "exp": "⭐"}

    text = f"{emoji_map.get(by, '🏆')} <b>Топ-20: {title_map.get(by, 'Богатейшие')}</b>\n\n"

    for i, user in enumerate(users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        if by == "money":
            value = format_money(user.balance)
        else:
            value = f"Ур. {user.level} ({user.exp} XP)"

        clan_tag = f"[{user.clan.tag}] " if user.clan else ""
        text += f"{medal} {clan_tag}{user.full_name} — <b>{value}</b>\n"

    await message.reply(text, parse_mode="HTML")


@router.message(Command("mystats"), GroupFilter)
async def cmd_mystats(message: Message, session: AsyncSession):
    """Show detailed stats for user."""
    user = await get_user_by_id(session, message.from_user.id)
    if not user:
        await message.reply("❌ Ты не зарегистрирован.")
        return

    progress, needed, percent = get_level_progress(user)

    # Calculate ranks
    from bot.database.crud import get_top_users
    money_top = await get_top_users(session, "money", 1000)
    level_top = await get_top_users(session, "level", 1000)

    money_rank = next((i for i, u in enumerate(money_top, 1) if u.id == user.id), "?")
    level_rank = next((i for i, u in enumerate(level_top, 1) if u.id == user.id), "?")

    text = (
        f"📊 <b>Подробная статистика: {user.full_name}</b>\n\n"
        f"💰 Баланс: <b>{format_money(user.balance)}</b> $ (топ {money_rank})\n"
        f"⭐ Уровень: Опыт: <b>{user.exp}</b> XP (топ {level_rank})\n"
        f"📈 Прогресс: <b>{progress}/{needed}</b> XP ({percent}%)\n"
        f"💼 Работа: <b>{user.job.name if user.job else 'Безработный'}</b>\n"
        f"🏰 Клан: <b>{f'[{user.clan.tag}] {user.clan.name}' if user.clan else 'Нет'}</b>\n"
        f"⚠️ Варнов: <b>{user.warns}/3</b>\n"
        f"🔥 Стрик: <b>{getattr(user, 'daily_streak', 0)}</b> дн.\n"
        f"📅 Регистрация: <b>{user.created_at.strftime('%d.%m.%Y')}</b>"
    )

    await message.reply(text, parse_mode="HTML")