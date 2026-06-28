from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    BigInteger,
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    Text,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs
import enum


class Base(AsyncAttrs, DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    MEMBER = "member"
    OFFICER = "officer"
    OWNER = "owner"


class BlacklistAction(str, enum.Enum):
    DELETE = "delete"
    WARN = "warn"
    MUTE = "mute"
    BAN = "ban"


class ModerationAction(str, enum.Enum):
    BAN = "ban"
    UNBAN = "unban"
    MUTE = "mute"
    UNMUTE = "unmute"
    WARN = "warn"
    UNWARN = "unwarn"
    BLACKLIST_TRIGGER = "blacklist_trigger"


class ItemType(str, enum.Enum):
    BOOST = "boost"
    PROTECTION = "protection"
    CONSUMABLE = "consumable"
    CLAN = "clan"
    SPECIAL = "special"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Job
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    job: Mapped[Optional["Job"]] = relationship(foreign_keys=[job_id])

    # Clan
    clan_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clans.id"), nullable=True)
    clan: Mapped[Optional["Clan"]] = relationship(foreign_keys=[clan_id])

    # Cooldowns
    last_daily: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_work: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_crime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_business_collect: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Moderation
    warns: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mute_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    jail_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    businesses: Mapped[List["UserBusiness"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    items: Mapped[List["UserItem"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    moderation_logs: Mapped[List["ModerationLog"]] = relationship(back_populates="user", foreign_keys="ModerationLog.user_id")
    clan_membership: Mapped[Optional["ClanMember"]] = relationship(back_populates="user", uselist=False)


class BlacklistWord(Base):
    __tablename__ = "blacklist_words"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(256), unique=True, nullable=False, index=True)
    normalized_word: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    regex_pattern: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    action: Mapped[BlacklistAction] = mapped_column(SQLEnum(BlacklistAction), default=BlacklistAction.WARN, nullable=False)
    duration_sec: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)  # for mute/ban
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_blacklist_words_normalized_active", "normalized_word", "is_active"),
    )


class ModerationLog(Base):
    __tablename__ = "moderation_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    admin_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    action: Mapped[ModerationAction] = mapped_column(SQLEnum(ModerationAction), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user: Mapped["User"] = relationship(foreign_keys=[user_id], back_populates="moderation_logs")
    admin: Mapped[Optional["User"]] = relationship(foreign_keys=[admin_id])


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    min_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    base_pay: Mapped[int] = mapped_column(Integer, nullable=False)
    exp_reward: Mapped[int] = mapped_column(Integer, nullable=False)
    cooldown_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)


class Crime(Base):
    __tablename__ = "crimes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    min_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    min_money: Mapped[int] = mapped_column(Integer, nullable=False)
    max_money: Mapped[int] = mapped_column(Integer, nullable=False)
    success_rate: Mapped[float] = mapped_column(nullable=False)  # 0.0 - 1.0
    jail_time_min: Mapped[int] = mapped_column(Integer, nullable=False)
    jail_time_max: Mapped[int] = mapped_column(Integer, nullable=False)
    exp_reward: Mapped[int] = mapped_column(Integer, nullable=False)
    cooldown_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    income_per_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    min_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_owned: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)


class UserBusiness(Base):
    __tablename__ = "user_businesses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    bought_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_collected: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="businesses")
    business: Mapped["Business"] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "business_id", name="uq_user_business"),
    )


class Clan(Base):
    __tablename__ = "clans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    tag: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    exp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    owner: Mapped["User"] = relationship(foreign_keys=[owner_id])
    members: Mapped[List["ClanMember"]] = relationship(back_populates="clan", cascade="all, delete-orphan")


class ClanMember(Base):
    __tablename__ = "clan_members"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    clan_id: Mapped[int] = mapped_column(ForeignKey("clans.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.MEMBER, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    clan: Mapped["Clan"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="clan_membership")

    __table_args__ = (
        UniqueConstraint("clan_id", "user_id", name="uq_clan_member"),
    )


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    type: Mapped[ItemType] = mapped_column(SQLEnum(ItemType), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    effect_json: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserItem(Base):
    __tablename__ = "user_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="items")
    item: Mapped["Item"] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_user_item"),
    )