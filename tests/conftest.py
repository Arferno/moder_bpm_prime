import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from bot.database.models import User, Job, Crime, Business, Item, ItemType, BlacklistWord, BlacklistAction, Clan, UserRole


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.delete = MagicMock()
    return session


@pytest.fixture
def mock_bot():
    """Mock aiogram Bot."""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.ban_chat_member = AsyncMock()
    bot.unban_chat_member = AsyncMock()
    bot.restrict_chat_member = AsyncMock()
    bot.get_me = AsyncMock(return_value=MagicMock(id=123456, username="test_bot"))
    return bot


@pytest.fixture
def sample_user():
    """Sample user for tests."""
    return User(
        id=1,
        tg_id=5459865698,
        username="testuser",
        full_name="Test User",
        balance=10000,
        exp=5000,
        level=10,
        job_id=3,
        clan_id=None,
        warns=0,
        is_banned=False,
        is_muted=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_job():
    """Sample job for tests."""
    return Job(
        id=1,
        name="Программист",
        min_level=10,
        base_pay=500,
        exp_reward=100,
        cooldown_sec=1800,
        description="Пишет код",
    )


@pytest.fixture
def sample_crime():
    """Sample crime for tests."""
    return Crime(
        id=1,
        name="Кража велосипеда",
        min_level=1,
        min_money=100,
        max_money=300,
        success_rate=0.7,
        jail_time_min=300,
        jail_time_max=600,
        exp_reward=20,
        cooldown_sec=600,
        description="Простая кража",
    )


@pytest.fixture
def sample_business():
    """Sample business for tests."""
    return Business(
        id=1,
        name="Кофейня",
        price=50000,
        income_per_hour=500,
        min_level=10,
        max_owned=3,
        description="Уютная кофейня",
    )


@pytest.fixture
def sample_item():
    """Sample item for tests."""
    return Item(
        id=1,
        name="Энергетик",
        type=ItemType.BOOST,
        price=500,
        effect_json={"money": 1000},
        description="Дает 1000$",
        is_active=True,
    )


@pytest.fixture
def sample_blacklist_word():
    """Sample blacklist word for tests."""
    return BlacklistWord(
        id=1,
        word="мат",
        normalized_word="мат",
        action=BlacklistAction.WARN,
        duration_sec=0,
        is_active=True,
        created_by=12345,
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_clan():
    """Sample clan for tests."""
    return Clan(
        id=1,
        name="Test Clan",
        tag="TST",
        owner_id=1,
        level=3,
        exp=10000,
        balance=50000,
        created_at=datetime.utcnow(),
    )