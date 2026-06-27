from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from bot.database.models import Clan, ClanMember, User, UserRole
from bot.database.crud import (
    get_clan,
    get_clan_members,
    get_clan_by_tag,
    get_top_clans,
)
from bot.config import settings


async def get_clan_info(session: AsyncSession, clan_id: int) -> Optional[dict]:
    """Returns detailed clan info."""
    clan = await get_clan(session, clan_id)
    if not clan:
        return None

    members = await get_clan_members(session, clan_id)
    member_count = len(members)

    # Calculate total clan exp from members
    total_exp = sum(m.user.exp for m in members if m.user)

    return {
        "clan": clan,
        "member_count": member_count,
        "total_exp": total_exp,
        "members": members,
    }


async def get_clan_top_members(session: AsyncSession, clan_id: int, limit: int = 10) -> List[ClanMember]:
    """Returns top clan members by contribution."""
    members = await get_clan_members(session, clan_id)
    # Sort by user exp (contribution)
    sorted_members = sorted(members, key=lambda m: m.user.exp if m.user else 0, reverse=True)
    return sorted_members[:limit]


async def calculate_clan_income(clan: Clan) -> int:
    """Calculates hourly clan income based on level and members."""
    base_income = clan.level * 1000
    # Bonus per member
    member_bonus = 50  # per member per hour
    return base_income + member_bonus


async def distribute_clan_income(session: AsyncSession) -> int:
    """
    Distributes clan income to clan treasury.
    Called hourly via scheduler.
    Returns number of clans processed.
    """
    from bot.database.connection import async_session_maker

    async with async_session_maker() as session:
        result = await session.execute(select(Clan))
        clans = result.scalars().all()

        for clan in clans:
            income = await calculate_clan_income(clan)
            clan.balance += income

        await session.flush()
        return len(clans)


async def add_clan_exp(session: AsyncSession, clan_id: int, exp: int) -> bool:
    """Adds experience to clan and handles level up."""
    clan = await get_clan(session, clan_id)
    if not clan:
        return False

    clan.exp += exp

    # Check level up
    new_level = clan.level
    while clan.exp >= get_exp_for_clan_level(new_level + 1):
        new_level += 1

    if new_level > clan.level:
        clan.level = new_level
        # Notify members (would need bot instance)

    await session.flush()
    return True


def get_exp_for_clan_level(level: int) -> int:
    """Returns XP required for clan level."""
    if level <= 1:
        return 0
    return level * level * 5000  # Much higher than user levels


async def promote_member(
    session: AsyncSession,
    clan_id: int,
    user_id: int,
    new_role: UserRole,
) -> bool:
    """Promotes/demotes clan member."""
    from bot.database.models import ClanMember
    from sqlalchemy import select

    result = await session.execute(
        select(ClanMember).where(
            ClanMember.clan_id == clan_id,
            ClanMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        return False

    member.role = new_role
    await session.flush()
    return True


async def kick_member(
    session: AsyncSession,
    clan_id: int,
    user_id: int,
) -> bool:
    """Kicks member from clan."""
    from bot.database.crud import leave_clan
    return await leave_clan(session, clan_id, user_id)


async def transfer_ownership(
    session: AsyncSession,
    clan_id: int,
    new_owner_id: int,
) -> bool:
    """Transfers clan ownership."""
    clan = await get_clan(session, clan_id)
    if not clan:
        return False

    # Check if new owner is member
    from bot.database.models import ClanMember
    from sqlalchemy import select

    result = await session.execute(
        select(ClanMember).where(
            ClanMember.clan_id == clan_id,
            ClanMember.user_id == new_owner_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        return False

    # Update old owner to officer
    old_owner_result = await session.execute(
        select(ClanMember).where(
            ClanMember.clan_id == clan_id,
            ClanMember.user_id == clan.owner_id,
        )
    )
    old_owner = old_owner_result.scalar_one_or_none()
    if old_owner:
        old_owner.role = UserRole.OFFICER

    # Update new owner
    member.role = UserRole.OWNER
    clan.owner_id = new_owner_id

    await session.flush()
    return True


async def disband_clan(
    session: AsyncSession,
    clan_id: int,
) -> bool:
    """Disbands clan completely."""
    from bot.database.models import ClanMember
    from sqlalchemy import delete

    # Remove all members
    await session.execute(delete(ClanMember).where(ClanMember.clan_id == clan_id))

    # Delete clan
    from bot.database.models import Clan
    await session.execute(delete(Clan).where(Clan.id == clan_id))

    await session.flush()
    return True


async def get_clan_leaderboard(
    session: AsyncSession,
    by: str = "level",
    limit: int = 10,
) -> List[Clan]:
    """Returns top clans leaderboard."""
    return await get_top_clans(session, by, limit)