from datetime import datetime
from typing import Optional


def format_money(amount: int) -> str:
    """Formats money with spaces as thousand separators."""
    return f"{amount:,}".replace(",", " ")


def format_number(num: int) -> str:
    """Formats number with spaces as thousand separators."""
    return f"{num:,}".replace(",", " ")


def format_time(seconds: int) -> str:
    """Formats seconds into human readable time."""
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} мин"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes:
            return f"{hours} ч {minutes} мин"
        return f"{hours} ч"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        if hours:
            return f"{days} д {hours} ч"
        return f"{days} д"


def format_datetime(dt: Optional[datetime]) -> str:
    """Formats datetime to string."""
    if dt is None:
        return "Никогда"
    return dt.strftime("%d.%m.%Y %H:%M")


def pluralize(count: int, forms: tuple[str, str, str]) -> str:
    """
    Russian pluralization.
    forms = (singular, few, many)
    e.g., pluralize(1, ("день", "дня", "дней")) -> "1 день"
    """
    count = abs(count)
    if count % 10 == 1 and count % 100 != 11:
        return forms[0]
    elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
        return forms[1]
    else:
        return forms[2]


def format_profile(user) -> str:
    """Formats user profile message."""
    from bot.utils.formatting import format_money

    job_name = user.job.name if user.job else "Безработный"
    clan_name = f"[{user.clan.tag}] {user.clan.name}" if user.clan else "Нет клана"

    # Progress bar for level
    from bot.utils.helpers import get_exp_for_next_level
    current_level_exp = get_exp_for_next_level(user.level - 1) if user.level > 1 else 0
    next_level_exp = get_exp_for_next_level(user.level)
    progress = user.exp - current_level_exp
    needed = next_level_exp - current_level_exp
    progress_percent = min(100, int((progress / needed) * 100)) if needed > 0 else 100

    bar_length = 10
    filled = int(bar_length * progress_percent / 100)
    bar = "█" * filled + "░" * (bar_length - filled)

    return (
        f"👤 <b>Профиль: {user.full_name}</b>\n"
        f"🆔 ID: <code>{user.tg_id}</code>\n"
        f"💰 Баланс: <b>{format_money(user.balance)}</b> $\n"
        f"⭐ Уровень: <b>{user.level}</b> ({progress}/{needed} XP)\n"
        f"   {bar} {progress_percent}%\n"
        f"💼 Работа: <b>{job_name}</b>\n"
        f"🏰 Клан: <b>{clan_name}</b>\n"
        f"⚠️ Варнов: <b>{user.warns}/3</b>\n"
        f"{'🔇 В муте' if user.is_muted else ''}"
        f"{' 🚫 Забанен' if user.is_banned else ''}"
        f"{' ⛓ В тюрьме' if user.jail_until else ''}"
    )


def format_job_info(job) -> str:
    """Formats job info for display."""
    return (
        f"💼 <b>{job.name}</b>\n"
        f"📝 {job.description or 'Нет описания'}\n"
        f"🔓 Уровень: <b>{job.min_level}</b>\n"
        f"💰 Оплата: <b>{format_money(job.base_pay)}</b> $\n"
        f"⭐ Опыт: <b>{job.exp_reward}</b> XP\n"
        f"⏳ Кулдаун: <b>{format_time(job.cooldown_sec)}</b>"
    )


def format_crime_info(crime) -> str:
    """Formats crime info for display."""
    success_pct = int(crime.success_rate * 100)
    return (
        f"🔫 <b>{crime.name}</b>\n"
        f"📝 {crime.description or 'Нет описания'}\n"
        f"🔓 Уровень: <b>{crime.min_level}</b>\n"
        f"💰 Награда: <b>{format_money(crime.min_money)}–{format_money(crime.max_money)}</b> $\n"
        f"⭐ Опыт: <b>{crime.exp_reward}</b> XP\n"
        f"✅ Шанс успеха: <b>{success_pct}%</b>\n"
        f"🏢 Тюрьма: <b>{format_time(crime.jail_time_min)}–{format_time(crime.jail_time_max)}</b>\n"
        f"⏳ Кулдаун: <b>{format_time(crime.cooldown_sec)}</b>"
    )


def format_business_info(business, owned_count: int = 0) -> str:
    """Formats business info for display."""
    max_owned = business.max_owned
    owned_str = f" ({owned_count}/{max_owned})" if owned_count > 0 else ""
    return (
        f"🏢 <b>{business.name}{owned_str}</b>\n"
        f"📝 {business.description or 'Нет описания'}\n"
        f"🔓 Уровень: <b>{business.min_level}</b>\n"
        f"💰 Цена: <b>{format_money(business.price)}</b> $\n"
        f"💵 Доход/час: <b>{format_money(business.income_per_hour)}</b> $\n"
        f"🔢 Макс. владение: <b>{max_owned}</b>"
    )


def format_clan_info(clan, members_count: int = 0, is_member: bool = False) -> str:
    """Formats clan info for display."""
    owner_tag = "👑" if is_member else ""
    return (
        f"🏰 <b>Клан [{clan.tag}] {clan.name}</b> {owner_tag}\n"
        f"👑 Владелец: <b>{clan.owner.full_name if clan.owner else 'Unknown'}</b>\n"
        f"📊 Уровень: <b>{clan.level}</b> ({clan.exp} XP)\n"
        f"💰 Казна: <b>{format_money(clan.balance)}</b> $\n"
        f"👥 Участников: <b>{members_count}</b>/50\n"
        f"📅 Создан: <b>{clan.created_at.strftime('%d.%m.%Y')}</b>"
    )


def format_item_info(item) -> str:
    """Formats item info for display."""
    type_emoji = {
        "boost": "⚡",
        "protection": "🛡",
        "consumable": "🧪",
        "clan": "🏰",
        "special": "✨",
    }.get(item.type.value, "📦")

    return (
        f"{type_emoji} <b>{item.name}</b>\n"
        f"📝 {item.description or 'Нет описания'}\n"
        f"💰 Цена: <b>{format_money(item.price)}</b> $\n"
        f"🎯 Тип: <b>{item.type.value}</b>"
    )