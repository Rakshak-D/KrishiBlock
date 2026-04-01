from __future__ import annotations

import secrets
from string import ascii_uppercase, digits
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


ModelT = TypeVar('ModelT')
ID_ALPHABET = ascii_uppercase + digits


def _random_suffix(length: int = 4) -> str:
    return ''.join(secrets.choice(ID_ALPHABET) for _ in range(length))


async def _generate_unique_id(db: AsyncSession, model: type[ModelT], prefix: str, attempts: int = 64) -> str:
    for _ in range(attempts):
        identifier = f'{prefix}-{_random_suffix()}'
        exists = await db.execute(select(getattr(model, 'id')).where(getattr(model, 'id') == identifier).limit(1))
        if exists.scalar_one_or_none() is None:
            return identifier
    raise RuntimeError(f'Unable to generate a unique identifier for prefix {prefix}.')


async def generate_user_id(db: AsyncSession) -> str:
    from app.models.user import User

    return await _generate_unique_id(db, User, 'AGR')


async def generate_wallet_id(db: AsyncSession) -> str:
    from app.models.wallet import Wallet

    return await _generate_unique_id(db, Wallet, 'WLT')


async def generate_listing_id(db: AsyncSession) -> str:
    from app.models.listing import Listing

    return await _generate_unique_id(db, Listing, 'LST')


async def generate_order_id(db: AsyncSession) -> str:
    from app.models.order import Order

    return await _generate_unique_id(db, Order, 'ORD')


async def generate_txn_id(db: AsyncSession) -> str:
    from app.models.transaction import Transaction

    return await _generate_unique_id(db, Transaction, 'TXN')


async def generate_withdrawal_id(db: AsyncSession) -> str:
    from app.models.wallet import WithdrawalRequest

    return await _generate_unique_id(db, WithdrawalRequest, 'WDR')


def generate_id(prefix: str) -> str:
    return f'{prefix}-{_random_suffix()}'


def generate_otp_code() -> str:
    return ''.join(secrets.choice(digits) for _ in range(6))


def generate_reference_token(length: int = 10) -> str:
    return ''.join(secrets.choice(ID_ALPHABET) for _ in range(length))
