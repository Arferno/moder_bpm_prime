from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.crud import get_user_by_id, get_or_create_user, get_top_users
from bot.services.farming_service import process_daily_reward, get_level_progress
from bot.handlers.farming import daily as daily_module, work as work_module, crime as crime_module, business as business_module, clan as clan_module
from bot.handlers import profile as profile_module, shop as shop_module, admin as admin_module
from bot.utils.formatting import format_money, format_profile
from bot.filters.chat_type import PrivateFilter
from bot.filters.is_admin import IsAdminFilter, IsSuperAdminFilter
from bot.keyboards.reply import main_menu_keyboard, admin_keyboard
from bot.utils.helpers import get_exp_for_next_level
from bot.utils.formatting import format_number


router = Router(name="text_commands")


# User buttons
@router.message(F.text == "👤 Профиль", PrivateFilter)
async def text_profile(message: Message, session: AsyncSession):
    await profile_module.cmd_profile(message, session)


@router.message(F.text == "💰 Баланс", PrivateFilter)
async def text_balance(message: Message, session: AsyncSession):
    await profile_module.cmd_balance(message, session)


@router.message(F.text == "📊 Топ", PrivateFilter)
async def text_top(message: Message, session: AsyncSession):
    await profile_module.cmd_top(message, session, CommandObject(args="money"))


@router.message(F.text == "🎁 Ежедневка", PrivateFilter)
async def text_daily(message: Message, session: AsyncSession):
    await daily_module.cmd_daily(message, session)


@router.message(F.text == "💼 Работа", PrivateFilter)
async def text_work(message: Message, session: AsyncSession):
    await work_module.cmd_work(message, session)


@router.message(F.text == "🔫 Преступления", PrivateFilter)
async def text_crime(message: Message, session: AsyncSession):
    await crime_module.cmd_crime(message, session)


@router.message(F.text == "🏢 Бизнес", PrivateFilter)
async def text_business(message: Message, session: AsyncSession):
    await business_module.cmd_business(message, session)


@router.message(F.text == "🏰 Клан", PrivateFilter)
async def text_clan(message: Message, session: AsyncSession):
    await clan_module.cmd_clan(message, session, CommandObject(args=""))


@router.message(F.text == "🛒 Магазин", PrivateFilter)
async def text_shop(message: Message, session: AsyncSession):
    await shop_module.cmd_shop(message, session, CommandObject(args=""))


@router.message(F.text == "🎒 Инвентарь", PrivateFilter)
async def text_inventory(message: Message, session: AsyncSession):
    await shop_module.cmd_inventory(message, session)


@router.message(F.text == "❓ Помощь", PrivateFilter)
async def text_help(message: Message, session: AsyncSession):
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username, message.from_user.full_name)
    await message.reply(
        "📖 <b>Помощь</b>\n\n"
        "🎁 <b>Ежедневка</b> — /daily — награда каждый день + бонус за стрик\n"
        "💼 <b>Работа</b> — /work — выбери работу, получай деньги и опыт\n"
        "🔫 <b>Преступления</b> — /crime — рискни за большие деньги (можешь попасть в тюрьму)\n"
        "🏢 <b>Бизнес</b> — /business — купи бизнесы для пассивного дохода\n"
        "🏰 <b>Клан</b> — /clan — создай или вступи в клан\n"
        "🛒 <b>Магазин</b> — /shop — купи предметы (бусты, защита, клановые)\n"
        "👤 <b>Профиль</b> — /profile — твой уровень, баланс, работа, клан\n"
        "💰 <b>Баланс</b> — /balance — твой баланс\n"
        "📊 <b>Топ</b> — /top — лучшие игроки\n\n"
        "⚙️ <b>Админ-команды</b> (только админы):\n"
        "/ban, /mute, /warn, /blacklist\n\n"
        "Напиши /start для главного меню.",
        parse_mode="HTML"
    )


# Admin buttons
@router.message(F.text == "📊 Статистика", PrivateFilter, IsSuperAdminFilter())
async def text_admin_stats(message: Message, session: AsyncSession):
    await admin_module.cmd_stats(message, session)


@router.message(F.text == "📢 Рассылка", PrivateFilter, IsSuperAdminFilter())
async def text_admin_broadcast(message: Message, session: AsyncSession):
    await message.reply(
        "📢 <b>Рассылка</b>\n\n"
        "Ответь на сообщение или напиши:\n"
        "<code>/broadcast Твой текст</code>\n\n"
        "Поддерживается HTML разметка.",
        parse_mode="HTML"
    )


@router.message(F.text == "💰 Выдать деньги", PrivateFilter, IsSuperAdminFilter())
async def text_admin_give_money(message: Message, session: AsyncSession):
    await message.reply(
        "💰 <b>Выдать деньги</b>\n\n"
        "Формат: <code>/give @user money 10000</code>\n\n"
        "Или ответь на сообщение пользователя командой.",
        parse_mode="HTML"
    )


@router.message(F.text == "⭐ Выдать опыт", PrivateFilter, IsSuperAdminFilter())
async def text_admin_give_exp(message: Message, session: AsyncSession):
    await message.reply(
        "⭐ <b>Выдать опыт</b>\n\n"
        "Формат: <code>/give @user exp 5000</code>",
        parse_mode="HTML"
    )


@router.message(F.text == "🔧 Установить уровень", PrivateFilter, IsSuperAdminFilter())
async def text_admin_setlevel(message: Message, session: AsyncSession):
    await message.reply(
        "🔧 <b>Установить уровень</b>\n\n"
        "Формат: <code>/setlevel @user 50</code>",
        parse_mode="HTML"
    )


@router.message(F.text == "🔄 Обновить ЧС", PrivateFilter, IsSuperAdminFilter())
async def text_admin_reload_bl(message: Message, session: AsyncSession):
    from bot.utils.text import invalidate_blacklist_cache
    await invalidate_blacklist_cache()
    from bot.database.crud import get_all_blacklist_words
    words = await get_all_blacklist_words(session)
    await message.reply(f"✅ Кэш ЧС обновлен. Слов: {len(words)}")


@router.message(F.text.in_(["👤 Профиль", "💰 Баланс"]), PrivateFilter, IsAdminFilter())
async def text_admin_profile_balance(message: Message, session: AsyncSession):
    if message.text == "👤 Профиль":
        await profile_module.cmd_profile(message, session)
    else:
        await profile_module.cmd_balance(message, session)