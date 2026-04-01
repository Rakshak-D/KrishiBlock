from __future__ import annotations

import asyncio
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models.listing import Listing, ListingMarketType, ListingStatus
from app.models.order import Order, OrderStatus
from app.models.transaction import Transaction
from app.models.user import User, UserType
from app.schemas import ListingPurchaseRequest
from app.services.mandi_price import get_mandi_price
from app.services.notification import send_notification
from app.services.qr_service import build_dpp, inr_to_usd
from app.services.wallet_service import place_order
from app.utils.escrow import build_release_key
from app.utils.serializers import decimal_to_float, envelope, serialize_datetime
from app.utils.traceability import build_listing_timeline, build_supply_flow, build_transaction_trail, build_transparency_payload


router = APIRouter(prefix='/api/listings', tags=['listings'])
ACTIVE_STATUSES = [ListingStatus.ACTIVE, ListingStatus.PARTIALLY_SOLD]
ALLOWED_SORT = {'newest', 'price'}


def _listing_card_payload(listing: Listing) -> dict[str, object | None]:
    usd_price = float(inr_to_usd(Decimal(listing.price_per_kg))) if listing.currency == 'INR' else float(listing.price_per_kg)
    return {
        'id': listing.id,
        'crop_name': listing.crop_name,
        'crop_label': listing.crop_name.title(),
        'price_per_kg': decimal_to_float(listing.price_per_kg),
        'usd_price_per_kg': usd_price,
        'currency': listing.currency,
        'market_type': listing.market_type.value,
        'quantity_remaining': decimal_to_float(listing.quantity_remaining),
        'status': listing.status.value,
        'farmer_name': listing.farmer.name,
        'village': listing.farmer.village,
        'reputation_score': float(listing.farmer.reputation_score),
        'gi_tag': listing.gi_tag,
        'organic_certified': listing.organic_certified,
        'created_at': serialize_datetime(listing.created_at),
    }


async def _query_listings(
    db: AsyncSession,
    *,
    market_type: ListingMarketType | None,
    crop: str | None,
    search: str | None,
    min_price: float | None,
    max_price: float | None,
    sort_by: str,
    page: int,
    page_size: int,
) -> tuple[list[Listing], int]:
    if sort_by not in ALLOWED_SORT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unsupported sort option.')

    filters = [Listing.status.in_(ACTIVE_STATUSES)]
    if market_type is not None:
        filters.append(Listing.market_type == market_type)
    if crop:
        filters.append(Listing.crop_name == crop.strip().lower())
    if min_price is not None:
        filters.append(Listing.price_per_kg >= min_price)
    if max_price is not None:
        filters.append(Listing.price_per_kg <= max_price)

    needs_farmer_join = False
    if search:
        search_term = f"%{search.strip().lower()}%"
        filters.append(
            or_(
                func.lower(Listing.crop_name).like(search_term),
                func.lower(User.name).like(search_term),
                func.lower(func.coalesce(User.village, '')).like(search_term),
            )
        )
        needs_farmer_join = True

    count_query = select(func.count(func.distinct(Listing.id)))
    data_query = select(Listing).options(selectinload(Listing.farmer))
    if needs_farmer_join:
        count_query = count_query.select_from(Listing).join(User, Listing.farmer_id == User.id)
        data_query = data_query.join(User, Listing.farmer_id == User.id)
    else:
        count_query = count_query.select_from(Listing)

    count_query = count_query.where(*filters)
    total_result = await db.execute(count_query)
    total = int(total_result.scalar_one())

    data_query = data_query.where(*filters)
    data_query = data_query.order_by(Listing.price_per_kg.asc() if sort_by == 'price' else Listing.created_at.desc())
    data_query = data_query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(data_query)
    return result.scalars().unique().all(), total


@router.get('')
async def get_listings(
    crop: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    sort_by: str = Query(default='newest'),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    listings, total = await _query_listings(
        db,
        market_type=ListingMarketType.LOCAL,
        crop=crop,
        search=search,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    return envelope({'items': [_listing_card_payload(item) for item in listings], 'total': total, 'page': page, 'page_size': page_size, 'has_more': page * page_size < total})


@router.get('/global')
async def get_global_listings(
    crop: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    sort_by: str = Query(default='newest'),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    listings, total = await _query_listings(
        db,
        market_type=ListingMarketType.GLOBAL,
        crop=crop,
        search=search,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    return envelope({'items': [_listing_card_payload(item) for item in listings], 'total': total, 'page': page, 'page_size': page_size, 'has_more': page * page_size < total})


async def _build_crop_highlights(db: AsyncSession) -> list[dict[str, object | None]]:
    result = await db.execute(
        select(
            Listing.crop_name,
            func.count(Listing.id).label('listing_count'),
            func.avg(Listing.price_per_kg).label('avg_price'),
            func.sum(Listing.quantity_remaining).label('total_volume'),
        )
        .where(Listing.status.in_(ACTIVE_STATUSES))
        .group_by(Listing.crop_name)
        .order_by(func.count(Listing.id).desc(), Listing.crop_name.asc())
        .limit(4)
    )
    rows = result.all()
    mandi_prices = await asyncio.gather(*(get_mandi_price(row.crop_name) for row in rows)) if rows else []
    highlights: list[dict[str, object | None]] = []
    for row, mandi_price in zip(rows, mandi_prices):
        average_price = float(row.avg_price or 0)
        highlights.append(
            {
                'crop_name': row.crop_name,
                'listing_count': int(row.listing_count or 0),
                'avg_price': round(average_price, 2),
                'total_volume': round(float(row.total_volume or 0), 2),
                'mandi_reference_price': round(float(mandi_price), 2),
                'price_delta': round(average_price - float(mandi_price), 2),
            }
        )
    return highlights


@router.get('/overview')
async def get_listings_overview(db: AsyncSession = Depends(get_db)) -> dict[str, object | None]:
    market_summary_result = await db.execute(
        select(
            Listing.market_type,
            func.count(Listing.id).label('listing_count'),
            func.sum(Listing.quantity_remaining).label('total_volume'),
            func.avg(Listing.price_per_kg).label('avg_price'),
        )
        .where(Listing.status.in_(ACTIVE_STATUSES))
        .group_by(Listing.market_type)
    )
    by_market = {
        market.value: {
            'listing_count': int(count or 0),
            'total_volume': round(float(total_volume or 0), 2),
            'avg_price': round(float(avg_price or 0), 2),
        }
        for market, count, total_volume, avg_price in market_summary_result.all()
    }
    for market_key in ('local', 'global'):
        by_market.setdefault(market_key, {'listing_count': 0, 'total_volume': 0.0, 'avg_price': 0.0})

    farmer_count_result = await db.execute(
        select(func.count(func.distinct(Listing.farmer_id))).where(Listing.status.in_(ACTIVE_STATUSES))
    )
    total_stock_result = await db.execute(
        select(func.sum(Listing.quantity_remaining)).where(Listing.status.in_(ACTIVE_STATUSES))
    )
    recent_result = await db.execute(
        select(Listing)
        .where(Listing.status.in_(ACTIVE_STATUSES))
        .options(selectinload(Listing.farmer))
        .order_by(Listing.created_at.desc())
        .limit(6)
    )

    return envelope(
        {
            'active_farmers': int(farmer_count_result.scalar_one() or 0),
            'total_listings': by_market['local']['listing_count'] + by_market['global']['listing_count'],
            'total_stock_kg': round(float(total_stock_result.scalar_one() or 0), 2),
            'by_market': by_market,
            'crop_highlights': await _build_crop_highlights(db),
            'recent_listings': [_listing_card_payload(item) for item in recent_result.scalars().unique().all()],
        }
    )


@router.get('/insights')
async def get_listing_insights(
    crop: str = Query(min_length=2, max_length=100),
    market_type: ListingMarketType | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    normalized_crop = crop.strip().lower()
    filters = [Listing.status.in_(ACTIVE_STATUSES), Listing.crop_name == normalized_crop]
    if market_type is not None:
        filters.append(Listing.market_type == market_type)

    summary_result = await db.execute(
        select(
            func.count(Listing.id).label('listing_count'),
            func.sum(Listing.quantity_remaining).label('total_volume'),
            func.avg(Listing.price_per_kg).label('avg_price'),
            func.min(Listing.price_per_kg).label('min_price'),
            func.max(Listing.price_per_kg).label('max_price'),
        ).where(*filters)
    )
    listing_count, total_volume, avg_price, min_price, max_price = summary_result.one()
    mandi_price = float(await get_mandi_price(normalized_crop))
    average_price = float(avg_price or 0)
    lower_band = round(mandi_price * 0.9, 2)
    upper_band = round(mandi_price * 1.1, 2)

    if average_price == 0:
        pricing_position = 'no_live_market_data'
    elif average_price < lower_band:
        pricing_position = 'below_reference'
    elif average_price > upper_band:
        pricing_position = 'above_reference'
    else:
        pricing_position = 'within_reference_band'

    return envelope(
        {
            'crop_name': normalized_crop,
            'market_type': market_type.value if market_type is not None else 'all',
            'listing_count': int(listing_count or 0),
            'total_volume': round(float(total_volume or 0), 2),
            'avg_price': round(average_price, 2),
            'min_price': round(float(min_price or 0), 2),
            'max_price': round(float(max_price or 0), 2),
            'mandi_reference_price': round(mandi_price, 2),
            'recommended_band': {'min': lower_band, 'max': upper_band},
            'pricing_position': pricing_position,
        }
    )


@router.get('/{listing_id}')
async def get_listing_detail(listing_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, object | None]:
    result = await db.execute(
        select(Listing)
        .where(Listing.id == listing_id)
        .options(selectinload(Listing.farmer), selectinload(Listing.orders).selectinload(Order.buyer))
    )
    listing = result.scalar_one_or_none()
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Listing not found.')

    reference_ids = [listing.id, *[order.id for order in listing.orders]]
    transaction_result = await db.execute(
        select(Transaction).where(Transaction.reference_id.in_(reference_ids)).order_by(Transaction.created_at.asc(), Transaction.id.asc())
    )
    transactions = transaction_result.scalars().all()

    delivered_count = sum(1 for order in listing.orders if order.status == OrderStatus.DELIVERED)
    dpp = build_dpp(listing, listing.farmer, list(listing.orders)) if listing.market_type == ListingMarketType.GLOBAL else None
    transparency = build_transparency_payload(listing, transactions)
    supply_flow = build_supply_flow(listing)

    return envelope(
        {
            **_listing_card_payload(listing),
            'quantity_kg': decimal_to_float(listing.quantity_kg),
            'quantity_sold': float(listing.quantity_kg - (listing.quantity_remaining or Decimal('0.00'))),
            'pickup_type': listing.pickup_type.value,
            'qr_code_path': listing.qr_code_path,
            'blockchain_hash': listing.blockchain_hash,
            'expires_at': serialize_datetime(listing.expires_at),
            'farmer': {
                'name': listing.farmer.name,
                'village': listing.farmer.village,
                'member_since': serialize_datetime(listing.farmer.created_at),
                'rating': float(listing.farmer.reputation_score),
                'successful_transactions': delivered_count,
                'total_sales': delivered_count,
            },
            'timeline': build_listing_timeline(listing),
            'supply_flow': supply_flow,
            'transparency': transparency,
            'order_count': len(listing.orders),
            'transaction_trail': build_transaction_trail(listing, transactions),
            'orders': [
                {
                    'id': order.id,
                    'buyer': f'Buyer {index + 1}',
                    'quantity_kg': decimal_to_float(order.quantity_kg),
                    'total_amount': decimal_to_float(order.total_amount),
                    'status': order.status.value,
                    'dispatched_at': serialize_datetime(order.dispatched_at),
                    'delivery_confirmed_at': serialize_datetime(order.delivery_confirmed_at),
                }
                for index, order in enumerate(sorted(listing.orders, key=lambda item: (item.created_at or '', item.id or '')))
            ],
            'dpp': dpp,
        }
    )


@router.post('/{listing_id}/buy')
async def buy_listing(
    listing_id: str,
    payload: ListingPurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    if current_user.user_type != UserType.BUYER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only buyers can place web orders.')

    result = await db.execute(select(Listing).where(Listing.id == listing_id).options(selectinload(Listing.farmer)))
    listing = result.scalar_one_or_none()
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Listing not found.')
    if listing.status not in ACTIVE_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='This listing is no longer available for purchase.')

    try:
        order = await place_order(db, buyer=current_user, listing=listing, quantity_kg=Decimal(str(payload.quantity_kg)))
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(order)

    await send_notification(
        listing.farmer.phone,
        'order_placed',
        {
            'buyer_city': current_user.village or 'buyer city',
            'qty': f'{order.quantity_kg:.2f}',
            'crop': listing.crop_name.title(),
        },
        listing.farmer.language,
    )
    await send_notification(
        listing.farmer.phone,
        'escrow_locked',
        {'amount': f'{order.total_amount:.2f}', 'deadline': '72 hours'},
        listing.farmer.language,
    )

    return envelope(
        {
            'order_id': order.id,
            'status': order.status.value,
            'quantity_kg': decimal_to_float(order.quantity_kg),
            'total_amount': decimal_to_float(order.total_amount),
            'platform_fee': decimal_to_float(order.platform_fee),
            'delivery_code': build_release_key(listing, order),
        }
    )





