from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserType(str, enum.Enum):
    FARMER = 'farmer'
    BUYER = 'buyer'


class MarketType(str, enum.Enum):
    LOCAL = 'local'
    GLOBAL = 'global'
    BOTH = 'both'


class User(Base):
    __tablename__ = 'users'

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    village: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_type: Mapped[UserType] = mapped_column(Enum(UserType, native_enum=False), nullable=False)
    language: Mapped[str] = mapped_column(String(5), default='en', nullable=False)
    market_type: Mapped[MarketType] = mapped_column(Enum(MarketType, native_enum=False), default=MarketType.LOCAL, nullable=False)
    reputation_score: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal('4.00'), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    wallet_address: Mapped[str | None] = mapped_column(String(48), unique=True, nullable=True, index=True)
    wallet_public_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    wallet_private_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    wallet = relationship('Wallet', back_populates='user', uselist=False, lazy='selectin')
    listings = relationship('Listing', back_populates='farmer', lazy='noload', foreign_keys='Listing.farmer_id')
    transactions = relationship('Transaction', back_populates='user', lazy='noload')
    orders = relationship('Order', back_populates='buyer', lazy='noload', foreign_keys='Order.buyer_id')
    withdrawals = relationship('WithdrawalRequest', back_populates='user', lazy='noload')

    def __repr__(self) -> str:
        return f'User(id={self.id!r}, phone={self.phone!r}, user_type={self.user_type.value!r})'
