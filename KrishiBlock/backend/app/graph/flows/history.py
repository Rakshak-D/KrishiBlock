from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.user import User
from app.utils.i18n import t


async def build_history_message(user: User, db: AsyncSession, language: str, limit: int = 10) -> str:
    result = await db.execute(
        select(Transaction).where(Transaction.user_id == user.id).order_by(Transaction.created_at.desc(), Transaction.id.desc()).limit(limit)
    )
    transactions = result.scalars().all()
    if not transactions:
        return t('history_empty', language)

    rows = [t('history_header', language)]
    for tx in transactions:
        rows.append(t('transaction_row', language, id=tx.id, type=tx.type.value, amount=f'{tx.amount:.2f}', ref=tx.reference_id or '-'))
    return '\n'.join(rows)
