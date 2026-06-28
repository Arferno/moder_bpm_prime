from datetime import datetime, timedelta
from typing import Optional, List, Sequence
from sqlalchemy import select, func, and_, or_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import (
    User,
    BlacklistWord,
    ModerationLog,
    Job,
    Crime,
    Business,
    UserBusiness,
    Clan,
    ClanMember,
    Item,
    UserItem,
    UserRole,
    ItemType,
    ModerationAction,
    BlacklistAction,
)
from bot.config import settings


# In-memory cache for blacklist
_blacklist_cache: List[BlacklistWord] = []
_blacklist_cache_time: Optional[datetime] = None


async def get_all_blacklist_words(session: AsyncSession) -> List[BlacklistWord]:
    result = await session.execute(
        select(BlacklistWord).where(BlacklistWord.is_active == True)
    )
    return result.scalars().all()


async def get_cached_blacklist(session: AsyncSession) -> List[BlacklistWord]:
    """Get blacklist words with in-memory caching (TTL from settings)."""
    global _blacklist_cache, _blacklist_cache_time
    
    now = datetime.utcnow()
    
    # Check if cache is valid
    if _blacklist_cache and _blacklist_cache_time:
        if (now - _blacklist_cache_time).total_seconds() < settings.blacklist_cache_ttl:
            return _blacklist_cache
    
    # Refresh cache
    words = await get_all_blacklist_words(session)
    _blacklist_cache = words
    _blacklist_cache_time = now
    return words


async def invalidate_blacklist_cache() -> None:
    """Invalidate in-memory blacklist cache."""
    global _blacklist_cache, _blacklist_cache_time
    _blacklist_cache = []
    _blacklist_cache_time = None


async def add_blacklist_word(
    session: AsyncSession,
    word: str,
    normalized_word: str,
    action: BlacklistAction,
    duration_sec: int,
    created_by: int,
    regex_pattern: Optional[str] = None,
) -> BlacklistWord:
    bl_word = BlacklistWord(
        word=word,
        normalized_word=normalized_word,
        regex_pattern=regex_pattern,
        action=action,
        duration_sec=duration_sec,
        created_by=created_by,
    )
    session.add(bl_word)
    await session.flush()
    await invalidate_blacklist_cache()
    return bl_word


async def remove_blacklist_word(session: AsyncSession, word: str) -> bool:
    result = await session.execute(
        delete(BlacklistWord).where(BlacklistWord.word == word)
    )
    await invalidate_blacklist_cache()
    return result.rowcount > 0


async def toggle_blacklist_word(session: AsyncSession, word: str) -> Optional[BlacklistWord]:
    result = await session.execute(
        select(BlacklistWord).where(BlacklistWord.word == word)
    )
    bl_word = result.scalar_one_or_none()
    if bl_word:
        bl_word.is_active = not bl_word.is_active
        await session.flush()
        await invalidate_blacklist_cache()
    return bl_word


# ==================== USER CRUD ====================

async def get_user(session: AsyncSession, tg_id: int) -> Optional[User]:
    result = await session.execute(
        select(User)
        .options(
            selectinload(User.job),
            selectinload(User.clan),
            selectinload(User.clan_membership),
        )
        .where(User.tg_id == tg_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    result = await session.execute(
        select(User)
        .options(
            selectinload(User.job),
            selectinload(User.clan),
            selectinload(User.clan_membership),
        )
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, tg_id: int, username: Optional[str], full_name: str) -> User:
    user = User(
        tg_id=tg_id,
        username=username,
        full_name=full_name,
    )
    session.add(user)
    await session.flush()
    return user


async def get_or_create_user(session: AsyncSession, tg_id: int, username: Optional[str], full_name: str) -> User:
    user = await get_user(session, tg_id)
    if user is None:
        user = await create_user(session, tg_id, username, full_name)
    return user


async def update_user_balance(session: AsyncSession, user_id: int, amount: int) -> User:
    user = await get_user_by_id(session, user_id)
    if user:
        user.balance += amount
        await session.flush()
    return user


async def update_user_exp(session: AsyncSession, user_id: int, amount: int) -> User:
    user = await get_user_by_id(session, user_id)
    if user:
        user.exp += amount
        await session.flush()
    return user


async def increment_user_warns(session: AsyncSession, user_id: int) -> int:
    user = await get_user_by_id(session, user_id)
    if user:
        user.warns += 1
        await session.flush()
        return user.warns
    return 0


async def decrement_user_warns(session: AsyncSession, user_id: int) -> int:
    user = await get_user_by_id(session, user_id)
    if user and user.warns > 0:
        user.warns -= 1
        await session.flush()
        return user.warns
    return 0


async def set_user_ban(session: AsyncSession, user_id: int, banned: bool) -> bool:
    user = await get_user_by_id(session, user_id)
    if user:
        user.is_banned = banned
        await session.flush()
        return True
    return False


async def set_user_mute(session: AsyncSession, user_id: int, muted: bool, until: Optional[datetime] = None) -> bool:
    user = await get_user_by_id(session, user_id)
    if user:
        user.is_muted = muted
        user.mute_until = until
        await session.flush()
        return True
    return False


async def set_user_jail(session: AsyncSession, user_id: int, until: Optional[datetime] = None) -> bool:
    user = await get_user_by_id(session, user_id)
    if user:
        user.jail_until = until
        await session.flush()
        return True
    return False


async def get_top_users(session: AsyncSession, by: str = "balance", limit: int = 10) -> Sequence[User]:
    order_col = User.balance if by == "balance" else User.exp if by == "level" else User.balance
    result = await session.execute(
        select(User)
        .where(User.is_banned == False)
        .order_by(order_col.desc())
        .limit(limit)
    )
    return result.scalars().all()


# ==================== MODERATION LOGS ====================

async def add_moderation_log(
    session: AsyncSession,
    user_id: int,
    action: ModerationAction,
    admin_id: Optional[int] = None,
    reason: Optional[str] = None,
    duration_sec: Optional[int] = None,
) -> ModerationLog:
    log = ModerationLog(
        user_id=user_id,
        admin_id=admin_id,
        action=action,
        reason=reason,
        duration_sec=duration_sec,
    )
    session.add(log)
    await session.flush()
    return log


async def get_user_warns_count(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count(ModerationLog.id)).where(
            and_(
                ModerationLog.user_id == user_id,
                ModerationLog.action == ModerationAction.WARN,
            )
        )
    )
    return result.scalar() or 0


async def get_user_moderation_logs(session: AsyncSession, user_id: int, limit: int = 20) -> Sequence[ModerationLog]:
    result = await session.execute(
        select(ModerationLog)
        .where(ModerationLog.user_id == user_id)
        .order_by(ModerationLog.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


# ==================== JOBS ====================

async def get_job(session: AsyncSession, job_id: int) -> Optional[Job]:
    result = await session.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def get_all_jobs(session: AsyncSession) -> Sequence[Job]:
    result = await session.execute(select(Job).order_by(Job.min_level))
    return result.scalars().all()


async def get_available_jobs(session: AsyncSession, user_level: int) -> Sequence[Job]:
    result = await session.execute(
        select(Job).where(Job.min_level <= user_level).order_by(Job.min_level)
    )
    return result.scalars().all()


async def get_user_job_cooldown(session: AsyncSession, user_id: int, job_id: int) -> Optional[int]:
    """Returns remaining cooldown seconds or None if not on cooldown."""
    from bot.database.models import User
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.last_work:
        return None
    from datetime import datetime, timedelta
    job = await get_job(session, job_id)
    if not job:
        return None
    elapsed = (datetime.utcnow() - user.last_work).total_seconds()
    remaining = job.cooldown_sec - int(elapsed)
    return max(0, remaining) if remaining > 0 else None


async def get_user_crime_cooldown(session: AsyncSession, user_id: int, crime_id: int) -> Optional[int]:
    """Returns remaining cooldown seconds or None if not on cooldown."""
    from bot.database.models import User
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.last_crime:
        return None
    from datetime import datetime
    crime = await get_crime(session, crime_id)
    if not crime:
        return None
    elapsed = (datetime.utcnow() - user.last_crime).total_seconds()
    remaining = crime.cooldown_sec - int(elapsed)
    return max(0, remaining) if remaining > 0 else None


# ==================== CRIMES ====================

async def get_crime(session: AsyncSession, crime_id: int) -> Optional[Crime]:
    result = await session.execute(select(Crime).where(Crime.id == crime_id))
    return result.scalar_one_or_none()


async def get_all_crimes(session: AsyncSession) -> Sequence[Crime]:
    result = await session.execute(select(Crime).order_by(Crime.min_level))
    return result.scalars().all()


async def get_available_crimes(session: AsyncSession, user_level: int) -> Sequence[Crime]:
    result = await session.execute(
        select(Crime).where(Crime.min_level <= user_level).order_by(Crime.min_level)
    )
    return result.scalars().all()


# ==================== BUSINESSES ====================

async def get_business(session: AsyncSession, business_id: int) -> Optional[Business]:
    result = await session.execute(select(Business).where(Business.id == business_id))
    return result.scalar_one_or_none()


async def get_all_businesses(session: AsyncSession) -> Sequence[Business]:
    result = await session.execute(select(Business).order_by(Business.price))
    return result.scalars().all()


async def get_user_businesses(session: AsyncSession, user_id: int) -> Sequence[UserBusiness]:
    result = await session.execute(
        select(UserBusiness)
        .options(selectinload(UserBusiness.business))
        .where(UserBusiness.user_id == user_id)
    )
    return result.scalars().all()


async def buy_business(session: AsyncSession, user_id: int, business_id: int) -> Optional[UserBusiness]:
    existing = await session.execute(
        select(UserBusiness).where(
            and_(UserBusiness.user_id == user_id, UserBusiness.business_id == business_id)
        )
    )
    if existing.scalar_one_or_none():
        return None

    ub = UserBusiness(user_id=user_id, business_id=business_id)
    session.add(ub)
    await session.flush()
    return ub


async def collect_business_income(session: AsyncSession, user_id: int) -> int:
    user_businesses = await get_user_businesses(session, user_id)
    total = 0
    now = datetime.utcnow()
    for ub in user_businesses:
        if ub.last_collected:
            hours_passed = (now - ub.last_collected).total_seconds() / 3600
        else:
            hours_passed = 0
        income = int(ub.business.income_per_hour * ub.level * hours_passed)
        if income > 0:
            total += income
            ub.last_collected = now
    await session.flush()
    return total


# ==================== CLANS ====================

async def create_clan(session: AsyncSession, name: str, tag: str, owner_id: int) -> Clan:
    clan = Clan(name=name, tag=tag.upper(), owner_id=owner_id)
    session.add(clan)
    await session.flush()

    member = ClanMember(clan_id=clan.id, user_id=owner_id, role=UserRole.OWNER)
    session.add(member)
    await session.flush()
    return clan


async def get_clan(session: AsyncSession, clan_id: int) -> Optional[Clan]:
    result = await session.execute(
        select(Clan).options(selectinload(Clan.owner)).where(Clan.id == clan_id)
    )
    return result.scalar_one_or_none()


async def get_clan_by_tag(session: AsyncSession, tag: str) -> Optional[Clan]:
    result = await session.execute(select(Clan).where(Clan.tag == tag.upper()))
    return result.scalar_one_or_none()


async def get_clan_members(session: AsyncSession, clan_id: int) -> Sequence[ClanMember]:
    result = await session.execute(
        select(ClanMember)
        .options(selectinload(ClanMember.user))
        .where(ClanMember.clan_id == clan_id)
        .order_by(ClanMember.role.desc(), ClanMember.joined_at)
    )
    return result.scalars().all()


async def join_clan(session: AsyncSession, clan_id: int, user_id: int) -> ClanMember:
    member = ClanMember(clan_id=clan_id, user_id=user_id, role=UserRole.MEMBER)
    session.add(member)
    await session.flush()
    return member


async def leave_clan(session: AsyncSession, clan_id: int, user_id: int) -> bool:
    result = await session.execute(
        delete(ClanMember).where(and_(ClanMember.clan_id == clan_id, ClanMember.user_id == user_id))
    )
    return result.rowcount > 0


async def get_top_clans(session: AsyncSession, by: str = "level", limit: int = 10) -> Sequence[Clan]:
    order_col = Clan.level if by == "level" else Clan.balance if by == "balance" else Clan.exp
    result = await session.execute(
        select(Clan).order_by(order_col.desc()).limit(limit)
    )
    return result.scalars().all()


# ==================== ITEMS ====================

async def get_item(session: AsyncSession, item_id: int) -> Optional[Item]:
    result = await session.execute(select(Item).where(Item.id == item_id))
    return result.scalar_one_or_none()


async def get_all_items(session: AsyncSession, type_: Optional[ItemType] = None) -> Sequence[Item]:
    query = select(Item).where(Item.is_active == True)
    if type_:
        query = query.where(Item.type == type_)
    result = await session.execute(query.order_by(Item.price))
    return result.scalars().all()


async def add_item_to_inventory(session: AsyncSession, user_id: int, item_id: int, quantity: int = 1) -> UserItem:
    existing = await session.execute(
        select(UserItem).where(and_(UserItem.user_id == user_id, UserItem.item_id == item_id))
    )
    ui = existing.scalar_one_or_none()
    if ui:
        ui.quantity += quantity
    else:
        ui = UserItem(user_id=user_id, item_id=item_id, quantity=quantity)
        session.add(ui)
    await session.flush()
    return ui


async def remove_item_from_inventory(session: AsyncSession, user_id: int, item_id: int, quantity: int = 1) -> bool:
    result = await session.execute(
        select(UserItem).where(and_(UserItem.user_id == user_id, UserItem.item_id == item_id))
    )
    ui = result.scalar_one_or_none()
    if ui:
        if ui.quantity <= quantity:
            await session.delete(ui)
        else:
            ui.quantity -= quantity
        await session.flush()
        return True
    return False


async def get_user_inventory(session: AsyncSession, user_id: int) -> Sequence[UserItem]:
    result = await session.execute(
        select(UserItem)
        .options(selectinload(UserItem.item))
        .where(UserItem.user_id == user_id)
    )
    return result.scalars().all()