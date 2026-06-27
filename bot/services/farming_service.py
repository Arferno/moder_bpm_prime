from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User, Job, Crime, Business, UserBusiness, Clan, ClanMember, UserRole
from bot.database.crud import (
    get_user_by_id,
    get_job,
    get_crime,
    get_business,
    get_user_businesses,
    get_clan,
    get_clan_members,
    collect_business_income,
)
from bot.utils.helpers import (
    get_exp_for_next_level,
    calculate_level_from_exp,
    calculate_work_reward,
    calculate_crime_reward,
    calculate_business_income,
    calculate_daily_reward,
    get_random_jail_time,
    check_level_up,
)
from bot.config import settings


# ==================== DAILY ====================

async def process_daily_reward(session: AsyncSession, user: User) -> Tuple[int, int, int]:
    """
    Processes daily reward for user.
    Returns (money_reward, exp_reward, new_streak).
    """
    now = datetime.utcnow()
    streak = 1

    if user.last_daily:
        diff = now - user.last_daily
        if diff < timedelta(hours=12):
            # Too early
            return 0, 0, 0
        elif diff < timedelta(hours=36):
            # Streak continues
            streak = getattr(user, 'daily_streak', 1) + 1
        else:
            # Streak broken
            streak = 1

    # Cap streak
    streak = min(streak, settings.max_streak_days)

    # Calculate reward
    money = calculate_daily_reward(
        settings.daily_base_reward,
        streak,
        settings.daily_streak_bonus,
        settings.max_streak_days,
    )
    exp = streak * 10  # Base exp + streak bonus

    # Apply clan bonus if in clan
    if user.clan_id:
        clan = await get_clan(session, user.clan_id)
        if clan and clan.level >= 3:
            money = int(money * 1.1)  # 10% bonus

    user.balance += money
    user.exp += exp
    user.last_daily = now
    user.daily_streak = streak

    # Check level up
    leveled_up = check_level_up(user)

    await session.flush()
    return money, exp, streak


# ==================== WORK ====================

async def process_work(
    session: AsyncSession,
    user: User,
    job_id: int,
) -> Tuple[bool, str, int, int]:
    """
    Processes work action.
    Returns (success, message, money, exp).
    """
    job = await get_job(session, job_id)
    if not job:
        return False, "Работа не найдена", 0, 0

    if user.level < job.min_level:
        return False, f"Нужен {job.min_level} уровень для этой работы", 0, 0

    # Check cooldown (stored in user.last_work)
    if user.last_work:
        from bot.database.crud import get_user_job_cooldown
        cooldown = await get_user_job_cooldown(session, user.id, job_id)
        if cooldown and cooldown > 0:
            return False, f"Подожди еще {cooldown} сек", 0, 0

    # Calculate reward
    money, exp = calculate_work_reward(job, user.level)

    # Apply clan bonus
    if user.clan_id:
        clan = await get_clan(session, user.clan_id)
        if clan and clan.level >= 2:
            money = int(money * 1.05)  # 5% bonus

    user.balance += money
    user.exp += exp
    user.job_id = job_id
    user.last_work = datetime.utcnow()

    # Check level up
    leveled_up = check_level_up(user)

    await session.flush()

    msg = f"✅ Работа выполнена!\n💰 +{money}$\n⭐ +{exp} XP"
    if leveled_up:
        msg += f"\n🎉 Новый уровень: {user.level}!"

    return True, msg, money, exp


# ==================== CRIME ====================

async def process_crime(
    session: AsyncSession,
    user: User,
    crime_id: int,
) -> Tuple[bool, str, int, int, Optional[int]]:
    """
    Processes crime action.
    Returns (success, message, money, exp, jail_time).
    """
    crime = await get_crime(session, crime_id)
    if not crime:
        return False, "Преступление не найдено", 0, 0, None

    if user.level < crime.min_level:
        return False, f"Нужен {crime.min_level} уровень", 0, 0, None

    # Check if in jail
    if user.jail_until and user.jail_until > datetime.utcnow():
        return False, "Ты в тюрьме! Не можешь совершать преступления", 0, 0, None

    # Check cooldown
    if user.last_crime:
        from bot.database.crud import get_user_crime_cooldown
        cooldown = await get_user_crime_cooldown(session, user.id, crime_id)
        if cooldown and cooldown > 0:
            return False, f"Подожди еще {cooldown} сек", 0, 0, None

    # Calculate outcome
    money, exp, success, jail_time = calculate_crime_reward(crime, user.level)

    if success:
        # Success
        user.balance += money
        user.exp += exp
        user.last_crime = datetime.utcnow()

        if jail_time:
            # Caught even on success
            user.jail_until = datetime.utcnow() + timedelta(seconds=jail_time)
            msg = f"🎉 Успех! Но тебя заметили...\n💰 +{money}$\n⭐ +{exp} XP\n🏢 Тюрьма на {jail_time//60} мин"
        else:
            msg = f"🎉 Успешно!\n💰 +{money}$\n⭐ +{exp} XP"

        # Check level up
        check_level_up(user)
    else:
        # Failed - go to jail
        user.jail_until = datetime.utcnow() + timedelta(seconds=jail_time)
        user.last_crime = datetime.utcnow()
        msg = f"🚫 Неудача! Тебя поймали.\n🏢 Тюрьма на {jail_time//60} мин"

    await session.flush()
    return success, msg, money, exp, jail_time


# ==================== BUSINESS ====================

async def buy_business(
    session: AsyncSession,
    user: User,
    business_id: int,
) -> Tuple[bool, str]:
    """Buys a business for user."""
    business = await get_business(session, business_id)
    if not business:
        return False, "Бизнес не найден"

    if user.level < business.min_level:
        return False, f"Нужен {business.min_level} уровень"

    # Check if already owns max
    user_businesses = await get_user_businesses(session, user.id)
    owned = next((ub for ub in user_businesses if ub.business_id == business_id), None)
    if owned and owned.level >= business.max_owned:
        return False, f"Максимум {business.max_owned} таких бизнесов"

    if user.balance < business.price:
        return False, "Недостаточно денег"

    # Buy
    user.balance -= business.price
    if owned:
        owned.level += 1
    else:
        from bot.database.crud import buy_business as crud_buy_business
        await crud_buy_business(session, user.id, business_id)

    await session.flush()
    return True, f"✅ Куплен бизнес: {business.name}!"


async def collect_business(
    session: AsyncSession,
    user: User,
) -> Tuple[int, str]:
    """Collects income from all user businesses."""
    total = await collect_business_income(session, user.id)
    if total > 0:
        user.balance += total
        await session.flush()
        return total, f"💰 Собрано: {total}$"
    return 0, "Нет дохода для сбора"


async def upgrade_business(
    session: AsyncSession,
    user: User,
    business_id: int,
) -> Tuple[bool, str]:
    """Upgrades a business (increases level)."""
    user_businesses = await get_user_businesses(session, user.id)
    ub = next((ub for ub in user_businesses if ub.business_id == business_id), None)

    if not ub:
        return False, "У тебя нет этого бизнеса"

    business = await get_business(session, business_id)
    if not business:
        return False, "Бизнес не найден"

    upgrade_price = business.price * ub.level // 2  # 50% of base price per level

    if user.balance < upgrade_price:
        return False, f"Нужно {upgrade_price}$ для улучшения"

    user.balance -= upgrade_price
    ub.level += 1
    await session.flush()

    return True, f"✅ {business.name} улучшен до {ub.level} уровня!"


# ==================== CLAN ====================

async def create_clan(
    session: AsyncSession,
    user: User,
    name: str,
    tag: str,
) -> Tuple[bool, str]:
    """Creates a new clan."""
    if user.clan_id:
        return False, "Ты уже в клане"

    if user.balance < 100000:
        return False, "Нужно 100,000$ для создания клана"

    # Check tag uniqueness
    existing = await get_clan_by_tag(session, tag)
    if existing:
        return False, "Такой тег уже занят"

    user.balance -= 100000
    from bot.database.crud import create_clan as crud_create_clan
    clan = await crud_create_clan(session, name, tag.upper(), user.id)

    await session.flush()
    return True, f"✅ Клан [{clan.tag}] {clan.name} создан!"


async def join_clan(
    session: AsyncSession,
    user: User,
    tag: str,
) -> Tuple[bool, str]:
    """Joins a clan by tag."""
    if user.clan_id:
        return False, "Ты уже в клане"

    clan = await get_clan_by_tag(session, tag)
    if not clan:
        return False, "Клан не найден"

    # Check if clan is full
    members = await get_clan_members(session, clan.id)
    if len(members) >= 50:
        return False, "Клан полон"

    from bot.database.crud import join_clan as crud_join_clan
    await crud_join_clan(session, clan.id, user.id)

    await session.flush()
    return True, f"✅ Ты вступил в клан [{clan.tag}] {clan.name}!"


async def leave_clan(
    session: AsyncSession,
    user: User,
) -> Tuple[bool, str]:
    """Leaves current clan."""
    if not user.clan_id:
        return False, "Ты не в клане"

    clan = await get_clan(session, user.clan_id)
    if not clan:
        return False, "Клан не найден"

    if clan.owner_id == user.id:
        return False, "Владелец не может покинуть клан. Распусти его или передай владение."

    from bot.database.crud import leave_clan as crud_leave_clan
    await crud_leave_clan(session, user.clan_id, user.id)

    await session.flush()
    return True, "✅ Ты покинул клан"


async def get_clan_by_tag(session: AsyncSession, tag: str):
    """Helper to get clan by tag."""
    from bot.database.crud import get_clan_by_tag
    return await get_clan_by_tag(session, tag)


# ==================== LEVEL & EXP ====================

def get_exp_for_level(level: int) -> int:
    """Returns total XP required for a level."""
    return get_exp_for_next_level(level)


def get_level_progress(user: User) -> Tuple[int, int, int]:
    """
    Returns (current_exp_in_level, exp_needed_for_next, progress_percent).
    """
    current_level_exp = get_exp_for_next_level(user.level - 1) if user.level > 1 else 0
    next_level_exp = get_exp_for_next_level(user.level)
    progress = user.exp - current_level_exp
    needed = next_level_exp - current_level_exp
    percent = min(100, int((progress / needed) * 100)) if needed > 0 else 100
    return progress, needed, percent