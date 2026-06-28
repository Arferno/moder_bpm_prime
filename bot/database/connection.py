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

print(f"=== ENGINE CREATED: {settings.database_url[:50]}... ===", flush=True)

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
    
    print("=== INIT_DB: Starting database initialization ===", flush=True)
    print(f"=== INIT_DB: Database URL: {settings.database_url[:50]}... ===", flush=True)
    
    # Retry logic for database connection
    max_retries = 10
    base_delay = 2  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"=== INIT_DB: Attempt {attempt}/{max_retries} ===", flush=True)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("=== INIT_DB: Database initialized successfully ===", flush=True)
            return
        except OperationalError as e:
            print(f"=== INIT_DB: Attempt {attempt} failed: {e} ===", flush=True)
            if attempt == max_retries:
                print(f"=== INIT_DB: Failed after {max_retries} attempts ===", flush=True)
                raise
            
            delay = base_delay * (2 ** (attempt - 1))
            print(f"=== INIT_DB: Retrying in {delay}s... ===", flush=True)
            await asyncio.sleep(delay)
        except Exception as e:
            print(f"=== INIT_DB: Unexpected error: {e} ===", flush=True)
            raise


async def close_db() -> None:
    await engine.dispose()