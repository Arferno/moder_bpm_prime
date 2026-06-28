import asyncio
import logging
import sys
from contextlib import asynccontextmanager

# IMMEDIATE STARTUP LOG - will show regardless of log level
print("=== BOT STARTING ===", flush=True)

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
print(f"=== CONFIG LOADED: {settings.bot_token[:10]}... ===", flush=True)

from bot.database.connection import init_db, close_db, async_session_maker
print("=== DB MODULE LOADED ===", flush=True)

from bot.middlewares.registration import RegistrationMiddleware
from bot.middlewares.blacklist import BlacklistMiddleware
from bot.middlewares.throttle import ThrottlingMiddleware
print("=== MIDDLEWARES LOADED ===", flush=True)

from bot.handlers import (
    moderation,
    profile,
    shop,
    admin,
)
from bot.handlers.farming import (
    daily,
    work,
    crime,
    business,
    clan,
)
from bot.services.moderation_service import check_and_unmute_expired
from apscheduler.schedulers.asyncio import AsyncIOScheduler

print("=== HANDLERS LOADED ===", flush=True)


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

print("=== LOGGING CONFIGURED ===", flush=True)


# Global bot instance
bot: Bot = None
dp: Dispatcher = None
scheduler: AsyncIOScheduler = None


@asynccontextmanager
async def lifespan():
    """Application lifespan handler."""
    global bot, dp, scheduler

    print("=== LIFESPAN START ===", flush=True)
    
    # Initialize database
    print("=== INIT DB START ===", flush=True)
    await init_db()
    print("=== INIT DB DONE ===", flush=True)

    # Create bot and dispatcher
    print("=== CREATING BOT ===", flush=True)
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    print("=== BOT CREATED ===", flush=True)

    # Register middlewares (order matters!)
    dp.message.middleware(RegistrationMiddleware())
    dp.message.middleware(ThrottlingMiddleware())
    dp.message.middleware(BlacklistMiddleware())
    dp.callback_query.middleware(RegistrationMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())
    print("=== MIDDLEWARES REGISTERED ===", flush=True)

    # Register routers
    dp.include_router(moderation.router)
    dp.include_router(daily.router)
    dp.include_router(work.router)
    dp.include_router(crime.router)
    dp.include_router(business.router)
    dp.include_router(clan.router)
    dp.include_router(profile.router)
    dp.include_router(shop.router)
    dp.include_router(admin.router)
    print("=== ROUTERS REGISTERED ===", flush=True)

    # Delete webhook if exists (important for polling)
    await bot.delete_webhook(drop_pending_updates=True)
    print("=== WEBHOOK DELETED ===", flush=True)

    # Start scheduler for periodic tasks
    print("=== STARTING SCHEDULER ===", flush=True)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_and_unmute_expired,
        "interval",
        minutes=1,
        args=[async_session_maker(), bot],
        id="check_unmute",
        replace_existing=True,
    )
    scheduler.add_job(
        collect_business_income_job,
        "interval",
        hours=1,
        args=[async_session_maker(), bot],
        id="collect_business",
        replace_existing=True,
    )
    scheduler.add_job(
        distribute_clan_income_job,
        "interval",
        hours=1,
        args=[async_session_maker()],
        id="distribute_clan",
        replace_existing=True,
    )
    scheduler.start()
    print("=== SCHEDULER STARTED ===", flush=True)

    # Log bot info
    me = await bot.get_me()
    print(f"=== BOT STARTED: @{me.username} ({me.id}) ===", flush=True)

    try:
        yield
    finally:
        # Cleanup
        print("=== SHUTTING DOWN ===", flush=True)
        scheduler.shutdown()
        await close_db()
        await bot.session.close()
        print("=== SHUTDOWN COMPLETE ===", flush=True)


async def collect_business_income_job(session_maker, bot: Bot):
    """Periodic job to collect business income for all users."""
    from bot.database.crud import get_all_businesses
    from bot.services.farming_service import calculate_business_income
    from sqlalchemy import select
    from bot.database.models import UserBusiness

    async with session_maker() as session:
        result = await session.execute(select(UserBusiness))
        user_businesses = result.scalars().all()

        for ub in user_businesses:
            # This is simplified - in reality you'd calculate per user
            pass


async def distribute_clan_income_job(session_maker):
    """Periodic job to distribute clan income."""
    from bot.services.clan_service import distribute_clan_income
    async with session_maker() as session:
        await distribute_clan_income(session)


async def main():
    """Main entry point."""
    async with lifespan():
        print("=== STARTING POLLING ===", flush=True)
        # Start polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)