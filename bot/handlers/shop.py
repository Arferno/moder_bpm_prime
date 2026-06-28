from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.crud import (
    get_user_by_id,
    get_all_items,
    get_user_inventory,
    add_item_to_inventory,
    remove_item_from_inventory,
    get_item,
)
from bot.database.models import ItemType
from bot.keyboards.inline import shop_keyboard, items_keyboard, inventory_keyboard
from bot.utils.formatting import format_money, format_item_info
from bot.filters.chat_type import GroupFilter
from bot.config import settings


router = Router(name="shop")


SHOP_CATEGORIES = ["all", "boost", "protection", "consumable", "clan", "special"]


@router.message(Command("shop"), GroupFilter)
async def cmd_shop(message: Message, session: AsyncSession, command: CommandObject):
    """Show shop."""
    user = await get_user_by_id(session, message.from_user.id)
    if not user:
        await message.reply("❌ Ты не зарегистрирован. Напиши /start в группе.")
        return

    category = "all"
    if command.args:
        cat = command.args.lower()
        if cat in SHOP_CATEGORIES:
            category = cat

    items = await get_all_items(session)
    if category != "all":
        try:
            item_type = ItemType(category)
            items = [i for i in items if i.type == item_type]
        except ValueError:
            pass

    text = (
        f"🛒 <b>Магазин</b>\n\n"
        f"💰 Твой баланс: <b>{format_money(user.balance)}</b> $\n\n"
        f"Категория: <b>{category}</b>"
    )
    await message.reply(text, reply_markup=shop_keyboard(SHOP_CATEGORIES, category), parse_mode="HTML")


@router.callback_query(F.data.startswith("shop_cat:"))
async def cb_shop_cat(callback: CallbackQuery, session: AsyncSession):
    category = callback.data.split(":")[1]
    user = await get_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрирован", show_alert=True)
        return

    items = await get_all_items(session)
    if category != "all":
        try:
            item_type = ItemType(category)
            items = [i for i in items if i.type == item_type]
        except ValueError:
            pass

    text = (
        f"🛒 <b>Магазин — {category}</b>\n\n"
        f"💰 Баланс: <b>{format_money(user.balance)}</b> $"
    )
    await callback.message.edit_text(
        text,
        reply_markup=items_keyboard(items),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("shop_page:"))
async def cb_shop_page(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    user = await get_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрирован", show_alert=True)
        return

    # We need to know current category - for simplicity, show all
    items = await get_all_items(session)
    await callback.message.edit_reply_markup(reply_markup=items_keyboard(items, page=page))
    await callback.answer()


@router.callback_query(F.data.startswith("shop_buy:"))
async def cb_shop_buy(callback: CallbackQuery, session: AsyncSession):
    item_id = int(callback.data.split(":")[1])
    user = await get_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрирован", show_alert=True)
        return

    item = await get_item(session, item_id)
    if not item:
        await callback.answer("❌ Предмет не найден", show_alert=True)
        return

    if user.balance < item.price:
        await callback.answer(f"❌ Недостаточно денег! Нужно {format_money(item.price)}$", show_alert=True)
        return

    user.balance -= item.price
    await add_item_to_inventory(session, user.id, item_id)
    await session.flush()

    await callback.answer(f"✅ Куплен: {item.name}!", show_alert=True)

    # Refresh shop
    items = await get_all_items(session)
    await callback.message.edit_reply_markup(reply_markup=items_keyboard(items))


@router.callback_query(F.data == "shop_inventory")
async def cb_shop_inventory(callback: CallbackQuery, session: AsyncSession):
    user = await get_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрирован", show_alert=True)
        return

    inventory = await get_user_inventory(session, user.id)
    if not inventory:
        await callback.message.edit_text(
            "🎒 <b>Инвентарь пуст</b>",
            reply_markup=inventory_keyboard([]),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    text = f"🎒 <b>Инвентарь {user.full_name}</b>\n\n💰 Баланс: {format_money(user.balance)}$"
    await callback.message.edit_text(
        text,
        reply_markup=inventory_keyboard(inventory),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("inv_page:"))
async def cb_inv_page(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    user = await get_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрирован", show_alert=True)
        return

    inventory = await get_user_inventory(session, user.id)
    await callback.message.edit_reply_markup(reply_markup=inventory_keyboard(inventory, page=page))
    await callback.answer()


@router.callback_query(F.data.startswith("inv_use:"))
async def cb_inv_use(callback: CallbackQuery, session: AsyncSession):
    item_id = int(callback.data.split(":")[1])
    user = await get_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрирован", show_alert=True)
        return

    # Remove item
    success = await remove_item_from_inventory(session, user.id, item_id)
    if not success:
        await callback.answer("❌ Предмет не найден", show_alert=True)
        return

    item = await get_item(session, item_id)
    if not item:
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    # Apply item effect
    effect = item.effect_json
    msg = f"✅ Использован: {item.name}\n"

    if effect.get("money"):
        user.balance += effect["money"]
        msg += f"💰 +{format_money(effect['money'])}$\n"
    if effect.get("exp"):
        user.exp += effect["exp"]
        msg += f"⭐ +{effect['exp']} XP\n"
    if effect.get("unwarn"):
        from bot.database.crud import decrement_user_warns
        warns = await decrement_user_warns(session, user.id)
        msg += f"⚠️ Варн снят! Осталось: {warns}/3\n"
    if effect.get("unmute"):
        user.is_muted = False
        user.mute_until = None
        msg += f"🔊 Мут снят!\n"

    from bot.utils.helpers import check_level_up
    check_level_up(user)

    await session.flush()

    inventory = await get_user_inventory(session, user.id)
    await callback.message.edit_text(
        msg,
        reply_markup=inventory_keyboard(inventory),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "inv_close")
async def cb_inv_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "shop_back")
async def cb_shop_back(callback: CallbackQuery, session: AsyncSession):
    user = await get_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрирован", show_alert=True)
        return

    text = (
        f"🛒 <b>Магазин</b>\n\n"
        f"💰 Твой баланс: <b>{format_money(user.balance)}</b> $"
    )
    await callback.message.edit_text(
        text,
        reply_markup=shop_keyboard(SHOP_CATEGORIES, "all"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "shop_close")
async def cb_shop_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.message(Command("inventory"), GroupFilter)
async def cmd_inventory(message: Message, session: AsyncSession):
    """Show inventory directly."""
    user = await get_user_by_id(session, message.from_user.id)
    if not user:
        await message.reply("❌ Ты не зарегистрирован.")
        return

    inventory = await get_user_inventory(session, user.id)
    if not inventory:
        await message.reply("🎒 Инвентарь пуст. Купи что-нибудь в /shop")
        return

    text = f"🎒 <b>Инвентарь {user.full_name}</b>\n\n💰 Баланс: {format_money(user.balance)}$"
    await message.reply(text, reply_markup=inventory_keyboard(inventory), parse_mode="HTML")


@router.message(Command("buy"), GroupFilter)
async def cmd_buy(message: Message, session: AsyncSession, command: CommandObject):
    """Buy item directly: /buy <item_id> [count]"""
    user = await get_user_by_id(session, message.from_user.id)
    if not user:
        await message.reply("❌ Ты не зарегистрирован.")
        return

    if not command.args:
        await message.reply("❌ Укажи ID предмета: /buy <id> [кол-во]")
        return

    args = command.args.split()
    item_id = int(args[0]) if args[0].isdigit() else 0
    count = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1

    if item_id <= 0:
        await message.reply("❌ Неверный ID")
        return

    item = await get_item(session, item_id)
    if not item:
        await message.reply("❌ Предмет не найден")
        return

    total_price = item.price * count
    if user.balance < total_price:
        await message.reply(f"❌ Недостаточно денег! Нужно {format_money(total_price)}$")
        return

    user.balance -= total_price
    await add_item_to_inventory(session, user.id, item_id, count)
    await session.flush()

    await message.reply(f"✅ Куплено: {item.name} x{count} за {format_money(total_price)}$", parse_mode="HTML")