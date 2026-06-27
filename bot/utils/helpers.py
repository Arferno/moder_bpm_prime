from datetime import datetime, timedelta
from typing import Optional, List
import random


def get_exp_for_next_level(level: int) -> int:
    """Returns XP required for a given level (level 1 = 0 XP)."""
    if level <= 1:
        return 0
    # Formula: level^2 * 100
    return level * level * 100


def calculate_level_from_exp(exp: int) -> int:
    """Calculates level from total XP."""
    level = 1
    while get_exp_for_next_level(level + 1) <= exp:
        level += 1
    return level


def check_level_up(user) -> bool:
    """Checks if user should level up and updates level if needed."""
    new_level = calculate_level_from_exp(user.exp)
    if new_level > user.level:
        user.level = new_level
        return True
    return False


def calculate_work_reward(job, user_level: int) -> tuple[int, int]:
    """
    Calculates money and XP reward for a job.
    Base pay * (1 + user_level * 0.05) with some randomness.
    """
    level_bonus = 1 + (user_level * 0.05)
    money = int(job.base_pay * level_bonus * random.uniform(0.9, 1.1))
    exp = int(job.exp_reward * level_bonus * random.uniform(0.9, 1.1))
    return money, exp


def calculate_crime_reward(crime, user_level: int) -> tuple[int, int, bool, Optional[int]]:
    """
    Calculates crime outcome.
    Returns (money, exp, success, jail_time).
    jail_time is None if not caught, otherwise seconds.
    """
    success = random.random() < crime.success_rate

    if success:
        money = random.randint(crime.min_money, crime.max_money)
        exp = crime.exp_reward
        # Small chance to get caught even on success (5%)
        if random.random() < 0.05:
            jail_time = random.randint(crime.jail_time_min, crime.jail_time_max)
            return money, exp, True, jail_time
        return money, exp, True, None
    else:
        # Failed - go to jail
        jail_time = random.randint(crime.jail_time_min, crime.jail_time_max)
        return 0, 0, False, jail_time


def calculate_business_income(business, count: int, hours: float) -> int:
    """Calculates business income for given hours."""
    return int(business.income_per_hour * count * hours)


def calculate_daily_reward(base: int, streak: int, streak_bonus: int, max_streak: int) -> int:
    """Calculates daily reward with streak bonus."""
    effective_streak = min(streak, max_streak)
    bonus = effective_streak * streak_bonus
    return base + bonus


def get_random_jail_time(min_sec: int, max_sec: int) -> int:
    """Returns random jail time between min and max."""
    return random.randint(min_sec, max_sec)


def parse_time_string(time_str: str) -> Optional[int]:
    """
    Parses time string like '10m', '1h', '1d' into seconds.
    Returns None if invalid.
    """
    time_str = time_str.strip().lower()
    if not time_str:
        return None

    try:
        if time_str.endswith('s'):
            return int(time_str[:-1])
        elif time_str.endswith('m'):
            return int(time_str[:-1]) * 60
        elif time_str.endswith('h'):
            return int(time_str[:-1]) * 3600
        elif time_str.endswith('d'):
            return int(time_str[:-1]) * 86400
        else:
            # Assume seconds if no suffix
            return int(time_str)
    except ValueError:
        return None


def format_time_remaining(target: Optional[datetime]) -> str:
    """Formats time remaining until target datetime."""
    if target is None:
        return "Никогда"
    now = datetime.utcnow()
    if target <= now:
        return "Уже истекло"
    diff = target - now
    return format_seconds(diff.total_seconds())


def format_seconds(seconds: float) -> str:
    """Formats seconds into human readable string."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        return f"{seconds // 60} мин"
    elif seconds < 86400:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h} ч {m} мин" if m else f"{h} ч"
    else:
        d = seconds // 86400
        h = (seconds % 86400) // 3600
        return f"{d} д {h} ч" if h else f"{d} д"


def get_mention(user_id: int, name: str) -> str:
    """Returns HTML mention for user."""
    return f'<a href="tg://user?id={user_id}">{name}</a>'


def escape_html(text: str) -> str:
    """Escapes HTML special characters."""
    return text.replace("&", "&").replace("<", "<").replace(">", ">")


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncates text to max length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Splits list into chunks of given size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def paginate(items: List, page: int, per_page: int) -> tuple[List, int, int]:
    """
    Returns (page_items, total_pages, current_page).
    Page is 1-indexed.
    """
    total_pages = (len(items) + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], total_pages, page