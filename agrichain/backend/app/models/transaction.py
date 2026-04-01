from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, event, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TransactionType(str, enum.Enum):
    CREDIT = 'credit'
    DEBIT = 'debit'
    ESCROW_LOCK = 'escrow_lock'
    ESCROW_RELEASE = 'escrow_release'
    REFUND = 'refund'
    FEE = 'fee'
    WELCOME_BONUS = 'welcome_bonus'


class Transaction(Base):
    __tablename__ = 'transactions'

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(20), ForeignKey('users.id'), nullable=False, index=True)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType, native_enum=False), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship('User', back_populates='transactions')

    def __repr__(self) -> str:
        return f'Transaction(id={self.id!r}, user_id={self.user_id!r}, type={self.type.value!r})'


@event.listens_for(Transaction, 'before_update')
def _prevent_transaction_update(_mapper, _connection, _target: Transaction) -> None:
    raise ValueError('Transactions are immutable and cannot be updated.')


@event.listens_for(Transaction, 'before_delete')
def _prevent_transaction_delete(_mapper, _connection, _target: Transaction) -> None:
    raise ValueError('Transactions are immutable and cannot be deleted.')
