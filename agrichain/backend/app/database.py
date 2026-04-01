from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


settings = get_settings()
engine = create_async_engine(settings.async_database_url, echo=settings.is_development)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def ensure_runtime_schema() -> None:
    async with engine.begin() as connection:
        dialect = connection.dialect.name
        if dialect == 'postgresql':
            await connection.execute(text('ALTER TABLE orders ADD COLUMN IF NOT EXISTS dispatched_at TIMESTAMPTZ NULL'))
            await connection.execute(text('CREATE INDEX IF NOT EXISTS ix_orders_dispatched_at ON orders (dispatched_at)'))
        elif dialect == 'sqlite':
            columns = await connection.execute(text("PRAGMA table_info('orders')"))
            names = {row[1] for row in columns.fetchall()}
            if 'dispatched_at' not in names:
                await connection.execute(text('ALTER TABLE orders ADD COLUMN dispatched_at DATETIME NULL'))


async def init_db() -> None:
    from app.models import listing, order, transaction, user, wallet  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await ensure_runtime_schema()


async def close_db() -> None:
    await engine.dispose()
