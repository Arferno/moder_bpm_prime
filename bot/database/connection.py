import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import OperationalError
from bot.config import settings


logger = logging.getLogger(__name__)


engine = create_async_engine(
    settings.database_url,
    echo=settings.log_level == "DEBUG",
    poolclass=NullPool,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session


async def init_db() -> None:
    from bot.database.models import Base
    
    # Retry logic for database connection
    max_retries = 10
    base_delay = 2  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database initialized successfully")
            return
        except OperationalError as e:
            if attempt == max_retries:
                logger.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                raise
            
            delay = base_delay * (2 ** (attempt - 1))  # exponential backoff: 2, 4, 8, 16...
            logger.warning(f"Database connection attempt {attempt}/{max_retries} failed: {e}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
        except Exception as e:
            logger.error(f"Unexpected error during database initialization: {e}")
            raise


async def close_db() -> None:
    await engine.dispose()