from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


settings = get_settings()
engine = create_async_engine(settings.async_database_url, echo=settings.is_development)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def _get_table_names(sync_connection) -> set[str]:
    inspector = inspect(sync_connection)
    return set(inspector.get_table_names())


def _get_column_names(sync_connection, table_name: str) -> set[str]:
    inspector = inspect(sync_connection)
    return {column['name'] for column in inspector.get_columns(table_name)}


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def ensure_runtime_schema() -> None:
    async with engine.begin() as connection:
        dialect = connection.dialect.name
        tables = await connection.run_sync(_get_table_names)

        if 'orders' in tables:
            order_columns = await connection.run_sync(_get_column_names, 'orders')
            if 'dispatched_at' not in order_columns:
                column_type = 'TIMESTAMPTZ' if dialect == 'postgresql' else 'DATETIME'
                await connection.execute(text(f'ALTER TABLE orders ADD COLUMN dispatched_at {column_type} NULL'))
            if dialect == 'postgresql':
                await connection.execute(text('CREATE INDEX IF NOT EXISTS ix_orders_dispatched_at ON orders (dispatched_at)'))

        if 'users' in tables:
            user_columns = await connection.run_sync(_get_column_names, 'users')
            for column_name, definition in [
                ('wallet_address', 'VARCHAR(48) NULL'),
                ('wallet_public_key', 'TEXT NULL'),
                ('wallet_private_key_encrypted', 'TEXT NULL'),
            ]:
                if column_name not in user_columns:
                    await connection.execute(text(f'ALTER TABLE users ADD COLUMN {column_name} {definition}'))
            if dialect == 'postgresql':
                await connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_users_wallet_address ON users (wallet_address)'))
            else:
                await connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_users_wallet_address ON users (wallet_address)'))

        if 'transactions' in tables:
            tx_columns = await connection.run_sync(_get_column_names, 'transactions')
            additions = [
                ('transaction_hash', 'VARCHAR(255) NULL'),
                ('previous_hash', 'VARCHAR(255) NULL'),
                ('merkle_root', 'VARCHAR(255) NULL'),
                ('signature', 'TEXT NULL'),
                ('signer_public_key', 'TEXT NULL'),
                ('signer_address', 'VARCHAR(48) NULL'),
                ('block_height', 'INTEGER NULL'),
                ('difficulty', 'INTEGER NULL'),
                ('nonce', 'INTEGER NULL'),
                ('hash_rate_hps', 'DOUBLE PRECISION NULL' if dialect == 'postgresql' else 'FLOAT NULL'),
                ('hash_attempts', 'INTEGER NULL'),
                ('mining_duration_ms', 'INTEGER NULL'),
            ]
            for column_name, definition in additions:
                if column_name not in tx_columns:
                    await connection.execute(text(f'ALTER TABLE transactions ADD COLUMN {column_name} {definition}'))
            await connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_transactions_transaction_hash ON transactions (transaction_hash)'))
            await connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_transactions_block_height ON transactions (block_height)'))
            await connection.execute(text('CREATE INDEX IF NOT EXISTS ix_transactions_signer_address ON transactions (signer_address)'))


async def init_db() -> None:
    from app.models import listing, order, transaction, user, wallet  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await ensure_runtime_schema()


async def close_db() -> None:
    await engine.dispose()
