from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.crud import (
    get_user_by_id,
    get_all_businesses,
    get_user_businesses,
    buy_business as crud_buy_business,
    get_business,
)
from bot.services.farming_service import (
    buy_business,
    collect_business,
    upgrade_business,
)
from bot.keyboards.inline import businesses_keyboard
from bot.utils.formatting import format_money, format_business_info
from bot.filters.chat_type import GroupFilter


router = Router(name="business")


@router.message(Command("business"), GroupFilter())
async def cmd_business(message: Message, session: AsyncSession):
    """Show business menu."""
    user = await get_user_by_id(session, message.from_user.id)
    if not user:
        await message.reply("❌ Ты не зарегистрирован. Напиши /start в группе.")
        return

    businesses = await get_all_businesses(session)
    user_businesses = await get_user_businesses(session, user.id)

    if not businesses:
        await message.reply("😔 Бизнесы пока не добавлены.")
        return

    text = (
        f"🏢 <b>Бизнес-империя</b>\n\n"
        f"💰 Баланс: <b>{format_money(user.balance)}</b> $\n"
        f"🏢 Твоих бизнесов: <b>{len(user_businesses)}</b>\n\n"
        f"Выбери бизнес для покупки или нажми 'Собрать доход':"
    )
    await message.reply(text, reply_markup=businesses_keyboard(businesses, user_businesses), parse_mode="HTML")


@router.callback_query(F.data.startswith("business_buy:"))
async def cb_business_buy(callback: CallbackQuery, session: AsyncSession):
    """Buy business."""
    business_id = int(callback.data.split(":")[1])
    user = await get_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрирован", show_alert=True)
        return

    success, msg = await buy_business(session, user, business_id)
    if success:
        # Refresh keyboard
        businesses = await get_all_businesses(session)
        user_businesses = await get_user_businesses(session, user.id)
        await callback.message.edit_text(
            f"✅ <b>Покупка успешна!</b>\n\n{msg}\n\n"
            f"💰 Баланс: <b>{format_money(user.balance)}</b> $",
            reply_markup=businesses_keyboard(businesses, user_businesses),
            parse_mode="HTML",
        )
    else:
        await callback.answer(msg, show_alert=True)
    await callback.answer()


@router.callback_query(F.data == "business_collect")
async def cb_business_collect(callback: CallbackQuery, session: AsyncSession):
    """Collect income from all businesses."""
    user = await get_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрирован", show_alert=True)
        return

    total, msg = await collect_business(session, user)
    businesses = await get_all_businesses(session)
    user_businesses = await get_user_businesses(session, user.id)

    await callback.message.edit_text(
        f"✅ <b>Сбор дохода!</b>\n\n{msg}\n\n"
        f"💰 Баланс: <b>{format_money(user.balance)}</b> $",
        reply_markup=businesses_keyboard(businesses, user_businesses),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("business_page:"))
async def cb_business_page(callback: CallbackQuery, session: AsyncSession):
    """Pagination for businesses."""
    page = int(callback.data.split(":")[1])
    user = await get_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрирован", show_alert=True)
        return

    businesses = await get_all_businesses(session)
    user_businesses = await get_user_businesses(session, user.id)

    await callback.message.edit_reply_markup(
        reply_markup=businesses_keyboard(businesses, user_businesses, page=page)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("business_info:"))
async def cb_business_info(callback: CallbackQuery, session: AsyncSession):
    """Show business info."""
    business_id = int(callback.data.split(":")[1])
    business = await get_business(session, business_id)
    if not business:
        await callback.answer("❌ Не найдено", show_alert=True)
        return

    await callback.message.edit_text(
        format_business_info(business),
        reply_markup=businesses_keyboard([business], [], page=1),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "business_close")
async def cb_business_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.message(Command("businessinfo"), GroupFilter())
async def cmd_businessinfo(message: Message, session: AsyncSession, command: CommandObject):
    """Show business info: /businessinfo <id>"""
    if not command.args or not command.args.isdigit():
        await message.reply("❌ Укажи ID бизнеса: /businessinfo <id>")
        return

    business = await get_business(session, int(command.args))
    if not business:
        await message.reply("❌ Бизнес не найден")
        return

    await message.reply(format_business_info(business), parse_mode="HTML")