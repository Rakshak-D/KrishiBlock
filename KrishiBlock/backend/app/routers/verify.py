from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.listing import Listing, ListingMarketType
from app.models.order import Order
from app.models.transaction import Transaction
from app.services.qr_service import build_dpp
from app.utils.serializers import decimal_to_float, envelope, serialize_datetime
from app.utils.traceability import build_listing_timeline, build_supply_flow, build_transaction_trail, build_transparency_payload


router = APIRouter(prefix='/api/verify', tags=['verify'])


@router.get('/{listing_id}')
async def verify_listing(listing_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, object | None]:
    listing_result = await db.execute(
        select(Listing)
        .where(Listing.id == listing_id)
        .options(selectinload(Listing.farmer), selectinload(Listing.orders).selectinload(Order.buyer))
    )
    listing = listing_result.scalar_one_or_none()
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Listing not found.')

    reference_ids = [listing.id, *[order.id for order in listing.orders]]
    transaction_result = await db.execute(
        select(Transaction).where(Transaction.reference_id.in_(reference_ids)).order_by(Transaction.block_height.asc().nulls_last(), Transaction.created_at.asc(), Transaction.id.asc())
    )
    transactions = transaction_result.scalars().all()
    transparency = build_transparency_payload(listing, transactions)

    return envelope(
        {
            'listing_id': listing.id,
            'farmer': {
                'name': listing.farmer.name,
                'village': listing.farmer.village,
                'id': listing.farmer.id,
                'rating': float(listing.farmer.reputation_score),
            },
            'crop_name': listing.crop_name,
            'quantity_kg': decimal_to_float(listing.quantity_kg),
            'quantity_remaining': decimal_to_float(listing.quantity_remaining),
            'price_per_kg': decimal_to_float(listing.price_per_kg),
            'currency': listing.currency,
            'listed_date': serialize_datetime(listing.created_at),
            'status': listing.status.value,
            'timeline': build_listing_timeline(listing),
            'supply_flow': build_supply_flow(listing),
            'orders': [
                {
                    'id': order.id,
                    'buyer': f'Buyer {index + 1}',
                    'status': order.status.value,
                    'quantity_kg': decimal_to_float(order.quantity_kg),
                    'dispatched_at': serialize_datetime(order.dispatched_at),
                    'delivery_confirmed_at': serialize_datetime(order.delivery_confirmed_at),
                }
                for index, order in enumerate(sorted(list(listing.orders), key=lambda item: (item.created_at or '', item.id or '')))
            ],
            'hash_fingerprint': listing.blockchain_hash,
            'blockchain_verified': bool(transparency['blockchain_verified']),
            'transparency': transparency,
            'transaction_trail': build_transaction_trail(listing, transactions),
            'dpp': build_dpp(listing, listing.farmer, list(listing.orders)) if listing.market_type == ListingMarketType.GLOBAL else None,
        }
    )

