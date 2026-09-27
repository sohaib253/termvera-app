from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()


def _create_engine() -> AsyncEngine:
    if not settings.database_url.startswith("sqlite"):
        return create_async_engine(settings.database_url, pool_pre_ping=True)

    # SQLite backs the desktop install. Uploads, extraction progress and
    # analysis all write from separate sessions at once, so wait for a
    # lock rather than failing with "database is locked", and use WAL so
    # readers (the UI polling progress) never block the writer.
    sqlite_engine = create_async_engine(settings.database_url, connect_args={"timeout": 30})

    @event.listens_for(sqlite_engine.sync_engine, "connect")
    def _configure(dbapi_connection, _record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return sqlite_engine


engine = _create_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine, expire_on_commit=False, autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
