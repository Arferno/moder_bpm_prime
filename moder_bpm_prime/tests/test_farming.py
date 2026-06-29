import pytest
from bot.utils.helpers import (
    get_exp_for_next_level,
    calculate_level_from_exp,
    calculate_work_reward,
    calculate_crime_reward,
    calculate_daily_reward,
    parse_time_string,
    format_seconds,
)
from bot.database.models import Job, Crime


class TestExperience:
    """Tests for experience and level calculations."""

    def test_exp_for_level_1(self):
        assert get_exp_for_next_level(1) == 0

    def test_exp_for_level_2(self):
        assert get_exp_for_next_level(2) == 400  # 2^2 * 100

    def test_exp_for_level_10(self):
        assert get_exp_for_next_level(10) == 10000  # 10^2 * 100

    def test_calculate_level_from_exp_zero(self):
        assert calculate_level_from_exp(0) == 1

    def test_calculate_level_from_exp_399(self):
        assert calculate_level_from_exp(399) == 1

    def test_calculate_level_from_exp_400(self):
        assert calculate_level_from_exp(400) == 2

    def test_calculate_level_from_exp_10000(self):
        assert calculate_level_from_exp(10000) == 10


class TestWorkRewards:
    """Tests for work reward calculations."""

    @pytest.fixture
    def job(self):
        return Job(
            id=1,
            name="Тест",
            min_level=1,
            base_pay=100,
            exp_reward=20,
            cooldown_sec=300,
        )

    def test_base_reward_level_1(self, job):
        money, exp = calculate_work_reward(job, 1)
        # level_bonus = 1 + 1*0.05 = 1.05
        # money = 100 * 1.05 * random(0.9, 1.1) => 94.5 - 115.5
        assert 90 <= money <= 120
        assert 18 <= exp <= 24

    def test_higher_level_bonus(self, job):
        money_1, _ = calculate_work_reward(job, 1)
        money_10, _ = calculate_work_reward(job, 10)
        # Level 10 should give ~50% more
        assert money_10 > money_1 * 1.3


class TestCrimeRewards:
    """Tests for crime reward calculations."""

    @pytest.fixture
    def crime(self):
        return Crime(
            id=1,
            name="Тест",
            min_level=1,
            min_money=100,
            max_money=200,
            success_rate=0.5,
            jail_time_min=300,
            jail_time_max=600,
            exp_reward=50,
            cooldown_sec=600,
        )

    def test_crime_returns_tuple(self, crime):
        result = calculate_crime_reward(crime, 1)
        assert len(result) == 4
        money, exp, success, jail_time = result
        assert isinstance(money, int)
        assert isinstance(exp, int)
        assert isinstance(success, bool)
        assert jail_time is None or isinstance(jail_time, int)

    def test_success_gives_money(self, crime):
        # Run many times to test success rate
        successes = 0
        for _ in range(100):
            money, exp, success, jail = calculate_crime_reward(crime, 1)
            if success:
                successes += 1
                assert crime.min_money <= money <= crime.max_money
                assert exp == crime.exp_reward
        # Should be roughly 50% success rate
        assert 30 <= successes <= 70


class TestDailyRewards:
    """Tests for daily reward calculations."""

    def test_base_reward(self):
        reward = calculate_daily_reward(100, 1, 50, 30)
        assert reward == 100  # base + 1*50 = 150, but wait...

    def test_streak_bonus(self):
        # day 1: 100 + 50 = 150
        # day 7: 100 + 7*50 = 450
        reward_1 = calculate_daily_reward(100, 1, 50, 30)
        reward_7 = calculate_daily_reward(100, 7, 50, 30)
        reward_30 = calculate_daily_reward(100, 30, 50, 30)

        assert reward_1 == 150
        assert reward_7 == 450
        assert reward_30 == 1600  # capped at 30

    def test_streak_capped(self):
        reward_50 = calculate_daily_reward(100, 50, 50, 30)
        reward_30 = calculate_daily_reward(100, 30, 50, 30)
        assert reward_50 == reward_30


class TestTimeParsing:
    """Tests for time string parsing."""

    def test_seconds(self):
        assert parse_time_string("30s") == 30
        assert parse_time_string("30") == 30

    def test_minutes(self):
        assert parse_time_string("10m") == 600
        assert parse_time_string("1m") == 60

    def test_hours(self):
        assert parse_time_string("1h") == 3600
        assert parse_time_string("2h") == 7200

    def test_days(self):
        assert parse_time_string("1d") == 86400
        assert parse_time_string("7d") == 604800

    def test_invalid(self):
        assert parse_time_string("abc") is None
        assert parse_time_string("") is None
        assert parse_time_string("1x") is None


class TestTimeFormatting:
    """Tests for time formatting."""

    def test_seconds(self):
        assert format_seconds(30) == "30 сек"
        assert format_seconds(59) == "59 сек"

    def test_minutes(self):
        assert format_seconds(60) == "1 мин"
        assert format_seconds(120) == "2 мин"
        assert format_seconds(90) == "1 мин 30 сек"

    def test_hours(self):
        assert format_seconds(3600) == "1 ч"
        assert format_seconds(7200) == "2 ч"
        assert format_seconds(5400) == "1 ч 30 мин"

    def test_days(self):
        assert format_seconds(86400) == "1 д"
        assert format_seconds(172800) == "2 д"
        assert format_seconds(90000) == "1 д 1 ч"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])