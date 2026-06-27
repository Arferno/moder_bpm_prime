from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.database.models import Job, Crime, Business, Clan, Item, UserBusiness, UserItem
from typing import List, Optional


def jobs_list_keyboard(jobs: List[Job], current_job_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Keyboard for job selection."""
    builder = InlineKeyboardBuilder()

    for job in jobs:
        text = f"{'✅ ' if job.id == current_job_id else ''}{job.name} (лвл {job.min_level})"
        builder.button(text=text, callback_data=f"work_select:{job.id}")

    builder.button(text="❌ Отмена", callback_data="work_cancel")
    builder.adjust(1)
    return builder.as_markup()


def crimes_list_keyboard(crimes: List[Crime]) -> InlineKeyboardMarkup:
    """Keyboard for crime selection."""
    builder = InlineKeyboardBuilder()

    for crime in crimes:
        success_pct = int(crime.success_rate * 100)
        text = f"{crime.name} ({success_pct}% успех, {crime.min_money}–{crime.max_money}$)"
        builder.button(text=text, callback_data=f"crime_select:{crime.id}")

    builder.button(text="❌ Отмена", callback_data="crime_cancel")
    builder.adjust(1)
    return builder.as_markup()


def businesses_keyboard(
    businesses: List[Business],
    user_businesses: List[UserBusiness],
    page: int = 1,
    per_page: int = 5,
) -> InlineKeyboardMarkup:
    """Keyboard for business list with pagination."""
    builder = InlineKeyboardBuilder()

    # Create dict for quick lookup
    owned = {ub.business_id: ub for ub in user_businesses}

    start = (page - 1) * per_page
    end = start + per_page
    page_businesses = businesses[start:end]

    for business in page_businesses:
        ub = owned.get(business.id)
        owned_count = ub.level if ub else 0
        max_owned = business.max_owned
        status = "🟢" if ub else "⚪"
        if owned_count >= max_owned:
            status = "🔴"

        text = f"{status} {business.name} — {business.price}$ (доход: {business.income_per_hour}$/ч)"
        if ub:
            text += f" [куплено: {owned_count}/{max_owned}]"

        if owned_count < max_owned:
            builder.button(text=text, callback_data=f"business_buy:{business.id}")
        else:
            builder.button(text=text, callback_data=f"business_info:{business.id}")

    # Pagination
    total_pages = (len(businesses) + per_page - 1) // per_page
    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"business_page:{page-1}"))
        nav_buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"business_page:{page+1}"))
        builder.row(*nav_buttons)

    builder.button(text="💰 Собрать доход", callback_data="business_collect")
    builder.button(text="❌ Закрыть", callback_data="business_close")
    builder.adjust(1)
    return builder.as_markup()


def clan_keyboard(clan: Clan, is_member: bool, is_owner: bool = False) -> InlineKeyboardMarkup:
    """Keyboard for clan actions."""
    builder = InlineKeyboardBuilder()

    if not is_member:
        builder.button(text="📥 Вступить", callback_data=f"clan_join:{clan.id}")
    else:
        if is_owner:
            builder.button(text="⚙️ Управление", callback_data=f"clan_manage:{clan.id}")
        builder.button(text="👥 Участники", callback_data=f"clan_members:{clan.id}")
        builder.button(text="💰 Казна", callback_data=f"clan_treasury:{clan.id}")
        builder.button(text="🚪 Покинуть", callback_data=f"clan_leave:{clan.id}")

    builder.button(text="📊 Топ кланов", callback_data="clan_top")
    builder.button(text="❌ Закрыть", callback_data="clan_close")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def clan_manage_keyboard(clan: Clan) -> InlineKeyboardMarkup:
    """Keyboard for clan management (owner only)."""
    builder = InlineKeyboardBuilder()

    builder.button(text="👥 Участники", callback_data=f"clan_members:{clan.id}")
    builder.button(text="💰 Казна", callback_data=f"clan_treasury:{clan.id}")
    builder.button(text="📝 Изменить название", callback_data=f"clan_rename:{clan.id}")
    builder.button(text="🚫 Расставить/снять офицера", callback_data=f"clan_officers:{clan.id}")
    builder.button(text="🗑 Распустить клан", callback_data=f"clan_disband:{clan.id}")
    builder.button(text="◀️ Назад", callback_data=f"clan_info:{clan.id}")
    builder.adjust(2)
    return builder.as_markup()


def shop_keyboard(categories: List[str], current_category: str = "all") -> InlineKeyboardMarkup:
    """Keyboard for shop categories."""
    builder = InlineKeyboardBuilder()

    for cat in categories:
        text = f"{'✅ ' if cat == current_category else ''}{cat.capitalize()}"
        builder.button(text=text, callback_data=f"shop_cat:{cat}")

    builder.button(text="🎒 Инвентарь", callback_data="shop_inventory")
    builder.button(text="❌ Закрыть", callback_data="shop_close")
    builder.adjust(2)
    return builder.as_markup()


def items_keyboard(items: List[Item], page: int = 1, per_page: int = 5) -> InlineKeyboardMarkup:
    """Keyboard for items list with pagination."""
    builder = InlineKeyboardBuilder()

    start = (page - 1) * per_page
    end = start + per_page
    page_items = items[start:end]

    for item in page_items:
        type_emoji = {
            "boost": "⚡",
            "protection": "🛡",
            "consumable": "🧪",
            "clan": "🏰",
            "special": "✨",
        }.get(item.type.value, "📦")

        builder.button(
            text=f"{type_emoji} {item.name} — {item.price}$",
            callback_data=f"shop_buy:{item.id}"
        )

    # Pagination
    total_pages = (len(items) + per_page - 1) // per_page
    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"shop_page:{page-1}"))
        nav_buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"shop_page:{page+1}"))
        builder.row(*nav_buttons)

    builder.button(text="◀️ Назад к категориям", callback_data="shop_back")
    builder.button(text="❌ Закрыть", callback_data="shop_close")
    builder.adjust(1)
    return builder.as_markup()


def inventory_keyboard(items: List[UserItem], page: int = 1, per_page: int = 5) -> InlineKeyboardMarkup:
    """Keyboard for user inventory."""
    builder = InlineKeyboardBuilder()

    start = (page - 1) * per_page
    end = start + per_page
    page_items = items[start:end]

    for ui in page_items:
        type_emoji = {
            "boost": "⚡",
            "protection": "🛡",
            "consumable": "🧪",
            "clan": "🏰",
            "special": "✨",
        }.get(ui.item.type.value, "📦")

        builder.button(
            text=f"{type_emoji} {ui.item.name} x{ui.quantity}",
            callback_data=f"inv_use:{ui.item.id}"
        )

    # Pagination
    total_pages = (len(items) + per_page - 1) // per_page
    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"inv_page:{page-1}"))
        nav_buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"inv_page:{page+1}"))
        builder.row(*nav_buttons)

    builder.button(text="❌ Закрыть", callback_data="inv_close")
    builder.adjust(1)
    return builder.as_markup()


def confirm_keyboard(action: str, target_id: int) -> InlineKeyboardMarkup:
    """Confirmation keyboard for dangerous actions."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data=f"confirm:{action}:{target_id}")
    builder.button(text="❌ Нет", callback_data=f"cancel:{action}")
    builder.adjust(2)
    return builder.as_markup()


def pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str,
    extra_buttons: List[InlineKeyboardButton] = None,
) -> InlineKeyboardMarkup:
    """Generic pagination keyboard."""
    builder = InlineKeyboardBuilder()

    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"{callback_prefix}:{current_page-1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"{callback_prefix}:{current_page+1}"))

    if nav_buttons:
        builder.row(*nav_buttons)

    if extra_buttons:
        for btn in extra_buttons:
            builder.row(btn)

    return builder.as_markup()


def blacklist_keyboard(page: int = 1, per_page: int = 10) -> InlineKeyboardMarkup:
    """Keyboard for blacklist management."""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить слово", callback_data="bl_add")
    builder.button(text="📋 Список", callback_data=f"bl_list:{page}")
    builder.button(text="❌ Закрыть", callback_data="bl_close")
    builder.adjust(2, 1)
    return builder.as_markup()


def blacklist_word_keyboard(word_id: int) -> InlineKeyboardMarkup:
    """Keyboard for individual blacklist word actions."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Вкл/Выкл", callback_data=f"bl_toggle:{word_id}")
    builder.button(text="🗑 Удалить", callback_data=f"bl_del:{word_id}")
    builder.button(text="◀️ Назад", callback_data="bl_list:1")
    builder.adjust(2, 1)
    return builder.as_markup()