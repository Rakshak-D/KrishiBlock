from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WithdrawalStatus(str, enum.Enum):
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'


class Wallet(Base):
    __tablename__ = 'wallets'

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(20), ForeignKey('users.id'), unique=True, nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal('100.00'), nullable=False)
    locked_balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default='INR', nullable=False)
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship('User', back_populates='wallet')

    def __repr__(self) -> str:
        return f'Wallet(id={self.id!r}, user_id={self.user_id!r}, balance={self.balance!r})'


class WithdrawalRequest(Base):
    __tablename__ = 'withdrawal_requests'

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(20), ForeignKey('users.id'), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    upi_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[WithdrawalStatus] = mapped_column(Enum(WithdrawalStatus, native_enum=False), default=WithdrawalStatus.PROCESSING, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship('User', back_populates='withdrawals')

    def __repr__(self) -> str:
        return f'WithdrawalRequest(id={self.id!r}, user_id={self.user_id!r}, status={self.status.value!r})'
