"""Database session and connection management."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.src.gitpulse.common.config import settings


class Base(DeclarativeBase):
    pass


def get_normalized_database_url(url: str) -> str:
    """Ensure PostgreSQL URLs use the asyncpg async dialect."""
    if not url:
        return "sqlite+aiosqlite:///./gitpulse_dev.db"
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# Use configured DATABASE_URL (defaults to SQLite for local dev)
engine = create_async_engine(
    get_normalized_database_url(settings.DATABASE_URL),
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Initializes tables in database schema with SQLite auto-fallback."""
    global engine, AsyncSessionLocal

    # Ensure all ORM models are registered with Base.metadata before table creation
    import backend.src.gitpulse.storage.models  # noqa: F401

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        if "postgresql" in settings.DATABASE_URL:
            # Fall back to SQLite file for local dev / tests when Postgres is not running
            fallback_url = "sqlite+aiosqlite:///./gitpulse_dev.db"
            engine = create_async_engine(fallback_url, echo=False, future=True)
            AsyncSessionLocal = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        else:
            raise


async def get_db_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
