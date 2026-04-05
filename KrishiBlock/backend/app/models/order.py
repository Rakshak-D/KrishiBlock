from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrderStatus(str, enum.Enum):
    PENDING = 'pending'
    ESCROW_LOCKED = 'escrow_locked'
    IN_TRANSIT = 'in_transit'
    DELIVERED = 'delivered'
    DISPUTED = 'disputed'
    CANCELLED = 'cancelled'


class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    listing_id: Mapped[str] = mapped_column(String(20), ForeignKey('listings.id'), nullable=False, index=True)
    buyer_id: Mapped[str] = mapped_column(String(20), ForeignKey('users.id'), nullable=False, index=True)
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    platform_fee: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus, native_enum=False), default=OrderStatus.PENDING, nullable=False, index=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    listing = relationship('Listing', back_populates='orders')
    buyer = relationship('User', back_populates='orders', foreign_keys=[buyer_id])

    def __repr__(self) -> str:
        return f'Order(id={self.id!r}, buyer_id={self.buyer_id!r}, status={self.status.value!r})'
