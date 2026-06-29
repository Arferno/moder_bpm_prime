#!/usr/bin/env python3
"""
Seed database with initial data: jobs, crimes, businesses, items.
Run after migrations: python scripts/init_db.py
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.database.connection import init_db, async_session_maker
from bot.database.models import (
    Job, Crime, Business, Item, ItemType, BlacklistWord, BlacklistAction
)


JOBS_DATA = [
    {"name": "Разнорабочий", "min_level": 1, "base_pay": 50, "exp_reward": 10, "cooldown_sec": 300,
     "description": "Простая физическая работа для новичков. Маленькая зарплата, но надежная."},
    {"name": "Курьер", "min_level": 3, "base_pay": 120, "exp_reward": 25, "cooldown_sec": 600,
     "description": "Доставка посылок по городу. Нужно знать маршруты."},
    {"name": "Охранник", "min_level": 5, "base_pay": 200, "exp_reward": 40, "cooldown_sec": 900,
     "description": "Охрана складов и офисов. Ночные смены платят больше."},
    {"name": "Оператор колл-центра", "min_level": 8, "base_pay": 350, "exp_reward": 60, "cooldown_sec": 1200,
     "description": "Прием звонков клиентов. Стрессовая работа, но стабильная."},
    {"name": "Программист-джун", "min_level": 10, "base_pay": 500, "exp_reward": 100, "cooldown_sec": 1800,
     "description": "Написание кода под руководством сеньоров. Начало IT-карьеры."},
    {"name": "Сеньор-разработчик", "min_level": 20, "base_pay": 1500, "exp_reward": 300, "cooldown_sec": 3600,
     "description": "Архитектура систем, код-ревью, менторинг. Высокая ответственность."},
    {"name": "Тимлид", "min_level": 30, "base_pay": 3000, "exp_reward": 600, "cooldown_sec": 7200,
     "description": "Управление командой разработчиков, планирование спринтов."},
    {"name": "CTO", "min_level": 40, "base_pay": 6000, "exp_reward": 1200, "cooldown_sec": 14400,
     "description": "Техническое руководство всей компанией. Стратегические решения."},
    {"name": "Инвестор", "min_level": 50, "base_pay": 10000, "exp_reward": 2000, "cooldown_sec": 28800,
     "description": "Инвестиции в стартапы, управление портфелем. Риск и высокий доход."},
    {"name": "Основатель Unicorn", "min_level": 60, "base_pay": 25000, "exp_reward": 5000, "cooldown_sec": 43200,
     "description": "Создание миллиардных компаний. Элита технологического бизнеса."},
    {"name": "Технологический магнат", "min_level": 70, "base_pay": 50000, "exp_reward": 10000, "cooldown_sec": 86400,
     "description": "Управление империей. Твои решения меняют мир."},
]


CRIMES_DATA = [
    {"name": "Кража велосипеда", "min_level": 1, "min_money": 100, "max_money": 300,
     "success_rate": 0.7, "jail_time_min": 300, "jail_time_max": 600,
     "exp_reward": 20, "cooldown_sec": 600,
     "description": "Простая кража. Малый риск, малая награда."},
    {"name": "Взлом авто", "min_level": 5, "min_money": 500, "max_money": 1500,
     "success_rate": 0.6, "jail_time_min": 600, "jail_time_max": 1800,
     "exp_reward": 50, "cooldown_sec": 1200,
     "description": "Угон машины. Нужны навыки взлома."},
    {"name": "Ограбление магазина", "min_level": 10, "min_money": 2000, "max_money": 5000,
     "success_rate": 0.5, "jail_time_min": 1800, "jail_time_max": 3600,
     "exp_reward": 150, "cooldown_sec": 3600,
     "description": "Налет на небольшой магазин. Команда из 2-3 человек."},
    {"name": "Мошенничество с криптой", "min_level": 15, "min_money": 5000, "max_money": 15000,
     "success_rate": 0.45, "jail_time_min": 3600, "jail_time_max": 7200,
     "exp_reward": 300, "cooldown_sec": 7200,
     "description": "Фишинг, скам-проекты. Умная преступность."},
    {"name": "Ограбление банкомата", "min_level": 25, "min_money": 20000, "max_money": 50000,
     "success_rate": 0.35, "jail_time_min": 7200, "jail_time_max": 14400,
     "exp_reward": 800, "cooldown_sec": 14400,
     "description": "Взлом банкомата газовой резакой. Громко и опасно."},
    {"name": "Кража грузовика", "min_level": 35, "min_money": 50000, "max_money": 150000,
     "success_rate": 0.3, "jail_time_min": 14400, "jail_time_max": 28800,
     "exp_reward": 2000, "cooldown_sec": 28800,
     "description": "Перехват ценного груза. Требует banda."},
    {"name": "Ограбление банка", "min_level": 50, "min_money": 200000, "max_money": 500000,
     "success_rate": 0.2, "jail_time_min": 28800, "jail_time_max": 86400,
     "exp_reward": 5000, "cooldown_sec": 86400,
     "description": "Классика жанра. План на месяц, команда профи."},
    {"name": "Кибератака на корпорацию", "min_level": 65, "min_money": 500000, "max_money": 1500000,
     "success_rate": 0.15, "jail_time_min": 43200, "jail_time_max": 172800,
     "exp_reward": 15000, "cooldown_sec": 172800,
     "description": "Рансомвэр, кража данных, выкуп. Элитный хакер."},
]


BUSINESSES_DATA = [
    {"name": "Кофейня", "price": 50000, "income_per_hour": 500, "min_level": 10, "max_owned": 3,
     "description": "Уютное место с хорошим кофе. Стабильный доход."},
    {"name": "Магазин электроники", "price": 200000, "income_per_hour": 2000, "min_level": 15, "max_owned": 2,
     "description": "Продажа гаджетов. Сезонные скачки спроса."},
    {"name": "Автосервис", "price": 500000, "income_per_hour": 5000, "min_level": 20, "max_owned": 2,
     "description": "Ремонт машин. Всегда есть клиенты."},
    {"name": "Коворкинг", "price": 1000000, "income_per_hour": 10000, "min_level": 25, "max_owned": 3,
     "description": "Аренда рабочих мест. Тренд на удаленку."},
    {"name": "Микро-завод", "price": 5000000, "income_per_hour": 50000, "min_level": 35, "max_owned": 1,
     "description": "Производство деталей. Высокие маржи."},
    {"name": "IT-компания", "price": 15000000, "income_per_hour": 150000, "min_level": 45, "max_owned": 1,
     "description": "Разработка ПО, аутсорсинг. Масштабируемый бизнес."},
    {"name": "Дата-центр", "price": 50000000, "income_per_hour": 500000, "min_level": 60, "max_owned": 1,
     "description": "Облачные услуги, хостинг. Пассивный доход элиты."},
]


ITEMS_DATA = [
    # Boosts
    {"name": "Энергетик", "type": ItemType.BOOST, "price": 500,
     "effect_json": {"money": 1000}, "description": "Мгновенно дает 1,000$"},
    {"name": "Книга опыта", "type": ItemType.BOOST, "price": 2000,
     "effect_json": {"exp": 500}, "description": "Дает 500 XP"},
    {"name": "Удвоитель зарплаты", "type": ItemType.BOOST, "price": 10000,
     "effect_json": {"work_multiplier": 2, "duration_hours": 24}, "description": "x2 к зарплате от работы 24 часа"},

    # Protection
    {"name": "Анти-мут", "type": ItemType.PROTECTION, "price": 5000,
     "effect_json": {"unmute": True}, "description": "Снимает мут с тебя"},
    {"name": "Иммунитет к ЧС", "type": ItemType.PROTECTION, "price": 50000,
     "effect_json": {"blacklist_immunity_hours": 24}, "description": "24 часа иммунитета к черному списку"},
    {"name": "Подача на разбан", "type": ItemType.PROTECTION, "price": 100000,
     "effect_json": {"unban": True}, "description": "Разбанивает тебя из группы (1 раз)"},

    # Consumable
    {"name": "Лотерейный билет", "type": ItemType.CONSUMABLE, "price": 1000,
     "effect_json": {"money": 0, "lottery": True}, "description": "Шанс выиграть 10,000-1,000,000$"},
    {"name": "Снятие варна", "type": ItemType.CONSUMABLE, "price": 15000,
     "effect_json": {"unwarn": 1}, "description": "Снимает 1 предупреждение"},
    {"name": "Ключ от тюрьмы", "type": ItemType.CONSUMABLE, "price": 25000,
     "effect_json": {"unjail": True}, "description": "Мгновенно выводит из тюрьмы"},

    # Clan
    {"name": "Клановый баннер", "type": ItemType.CLAN, "price": 100000,
     "effect_json": {"clan_exp": 1000}, "description": "Дает клану 1,000 XP"},
    {"name": "Сокровищница клана", "type": ItemType.CLAN, "price": 500000,
     "effect_json": {"clan_money": 50000}, "description": "Пополняет казну клана на 50,000$"},

    # Special
    {"name": "Премиум-статус (30 дн.)", "type": ItemType.SPECIAL, "price": 100000,
     "effect_json": {"premium_days": 30}, "description": "+50% к всем доходам, уникальный тег в чате"},
    {"name": "Смена ника", "type": ItemType.SPECIAL, "price": 5000,
     "effect_json": {"rename": True}, "description": "Позволяет сменить отображаемое имя в боте"},
]


async def seed_jobs(session: AsyncSession):
    for job_data in JOBS_DATA:
        result = await session.execute(select(Job).where(Job.name == job_data["name"]))
        if not result.scalar_one_or_none():
            session.add(Job(**job_data))
    await session.flush()
    print(f"✅ Seeded {len(JOBS_DATA)} jobs")


async def seed_crimes(session: AsyncSession):
    for crime_data in CRIMES_DATA:
        result = await session.execute(select(Crime).where(Crime.name == crime_data["name"]))
        if not result.scalar_one_or_none():
            session.add(Crime(**crime_data))
    await session.flush()
    print(f"✅ Seeded {len(CRIMES_DATA)} crimes")


async def seed_businesses(session: AsyncSession):
    for biz_data in BUSINESSES_DATA:
        result = await session.execute(select(Business).where(Business.name == biz_data["name"]))
        if not result.scalar_one_or_none():
            session.add(Business(**biz_data))
    await session.flush()
    print(f"✅ Seeded {len(BUSINESSES_DATA)} businesses")


async def seed_items(session: AsyncSession):
    for item_data in ITEMS_DATA:
        result = await session.execute(select(Item).where(Item.name == item_data["name"]))
        if not result.scalar_one_or_none():
            session.add(Item(**item_data))
    await session.flush()
    print(f"✅ Seeded {len(ITEMS_DATA)} items")


async def seed_blacklist_words(session: AsyncSession):
    """Add some default blacklist words."""
    default_words = [
        ("реклама", BlacklistAction.MUTE, 3600),
        ("спам", BlacklistAction.MUTE, 1800),
        ("мат", BlacklistAction.WARN, 0),
        ("оскорбление", BlacklistAction.WARN, 0),
        ("продажа", BlacklistAction.DELETE, 0),
        ("куплю", BlacklistAction.DELETE, 0),
        ("продам", BlacklistAction.DELETE, 0),
        ("ссылка", BlacklistAction.DELETE, 0),
        ("t.me/", BlacklistAction.DELETE, 0),
        ("@username", BlacklistAction.DELETE, 0),
    ]

    from bot.utils.text import normalize_word_for_storage

    for word, action, duration in default_words:
        normalized = normalize_word_for_storage(word)
        result = await session.execute(select(BlacklistWord).where(BlacklistWord.normalized_word == normalized))
        if not result.scalar_one_or_none():
            session.add(BlacklistWord(
                word=word,
                normalized_word=normalized,
                action=action,
                duration_sec=duration,
                created_by=0,  # System
            ))
    await session.flush()
    print(f"✅ Seeded {len(default_words)} blacklist words")


async def main():
    print("🌱 Seeding database...")
    await init_db()

    async with async_session_maker() as session:
        await seed_jobs(session)
        await seed_crimes(session)
        await seed_businesses(session)
        await seed_items(session)
        await seed_blacklist_words(session)
        await session.commit()

    print("✅ Database seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())