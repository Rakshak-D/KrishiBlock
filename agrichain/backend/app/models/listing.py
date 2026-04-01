from __future__ import annotations

import enum
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, event, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PickupType(str, enum.Enum):
    AT_FARM = 'at_farm'
    NEAREST_MANDI = 'nearest_mandi'
    FARMER_DELIVERS = 'farmer_delivers'


class ListingStatus(str, enum.Enum):
    ACTIVE = 'active'
    PARTIALLY_SOLD = 'partially_sold'
    SOLD = 'sold'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'


class ListingMarketType(str, enum.Enum):
    LOCAL = 'local'
    GLOBAL = 'global'


class Listing(Base):
    __tablename__ = 'listings'

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    farmer_id: Mapped[str] = mapped_column(String(20), ForeignKey('users.id'), nullable=False, index=True)
    crop_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    quantity_remaining: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    price_per_kg: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default='INR', nullable=False)
    market_type: Mapped[ListingMarketType] = mapped_column(Enum(ListingMarketType, native_enum=False), default=ListingMarketType.LOCAL, nullable=False, index=True)
    pickup_type: Mapped[PickupType] = mapped_column(Enum(PickupType, native_enum=False), nullable=False)
    gi_tag: Mapped[str | None] = mapped_column(String(100), nullable=True)
    organic_certified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[ListingStatus] = mapped_column(Enum(ListingStatus, native_enum=False), default=ListingStatus.ACTIVE, nullable=False, index=True)
    qr_code_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    blockchain_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    farmer = relationship('User', back_populates='listings', foreign_keys=[farmer_id])
    orders = relationship('Order', back_populates='listing', lazy='selectin')

    def __repr__(self) -> str:
        return f'Listing(id={self.id!r}, crop_name={self.crop_name!r}, status={self.status.value!r})'


@event.listens_for(Listing, 'before_insert')
def _set_listing_defaults(_mapper, _connection, target: Listing) -> None:
    if target.quantity_remaining is None:
        target.quantity_remaining = target.quantity_kg
    if target.expires_at is None:
        target.expires_at = datetime.now(timezone.utc) + timedelta(hours=72)
