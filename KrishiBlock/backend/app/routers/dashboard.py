from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models.listing import Listing, ListingMarketType, ListingStatus, PickupType
from app.models.order import Order, OrderStatus
from app.models.transaction import Transaction, TransactionType
from app.models.user import MarketType, User, UserType
from app.schemas import ListingCreateRequest, ListingUpdateRequest, OrderConfirmRequest, ProfileUpdateRequest
from app.services.blockchain_sim import hash_listing
from app.services.mandi_price import get_mandi_price
from app.services.notification import send_notification
from app.services.qr_service import build_verify_url, generate_listing_qr, inr_to_usd
from app.services.wallet_service import anchor_listing_on_chain, cancel_listing, confirm_order_delivery, ensure_wallet, mark_order_in_transit, update_listing
from app.utils.escrow import build_release_key
from app.utils.id_generator import generate_listing_id
from app.utils.serializers import decimal_to_float, envelope, serialize_datetime
from app.utils.validators import validate_name


router = APIRouter(prefix='/api/dashboard', tags=['dashboard'])


def _resolve_listing_market(user: User, requested_market: str | None) -> ListingMarketType:
    if user.market_type == MarketType.BOTH:
        return ListingMarketType(requested_market or ListingMarketType.LOCAL.value)
    if user.market_type == MarketType.GLOBAL:
        return ListingMarketType.GLOBAL
    return ListingMarketType.LOCAL


def _listing_payload(listing: Listing) -> dict[str, object | None]:
    quantity_remaining = decimal_to_float(listing.quantity_remaining)
    quantity_total = decimal_to_float(listing.quantity_kg)
    sold_quantity = float(listing.quantity_kg - (listing.quantity_remaining or Decimal('0.00')))
    return {
        'id': listing.id,
        'crop_name': listing.crop_name,
        'quantity_kg': quantity_total,
        'quantity_remaining': quantity_remaining,
        'quantity_sold': sold_quantity,
        'price_per_kg': decimal_to_float(listing.price_per_kg),
        'usd_price_per_kg': float(inr_to_usd(listing.price_per_kg)) if listing.currency == 'INR' else float(listing.price_per_kg),
        'currency': listing.currency,
        'market_type': listing.market_type.value,
        'status': listing.status.value,
        'pickup_type': listing.pickup_type.value,
        'qr_code_path': listing.qr_code_path,
        'gi_tag': listing.gi_tag,
        'organic_certified': listing.organic_certified,
        'created_at': serialize_datetime(listing.created_at),
        'expires_at': serialize_datetime(listing.expires_at),
        'verify_url': build_verify_url(listing.id),
    }


@router.get('/overview')
async def overview(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict[str, object | None]:
    wallet = await ensure_wallet(db, current_user)
    recent_transactions_result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.block_height.desc().nulls_last(), Transaction.created_at.desc(), Transaction.id.desc())
        .limit(6)
    )
    recent_transactions = [
        {
            'id': tx.id,
            'type': tx.type.value,
            'amount': decimal_to_float(tx.amount),
            'balance_after': decimal_to_float(tx.balance_after),
            'reference_id': tx.reference_id,
            'description': tx.description,
            'created_at': serialize_datetime(tx.created_at),
        }
        for tx in recent_transactions_result.scalars().all()
    ]

    notifications: list[dict[str, object | None]] = []
    feed: dict[str, object] = {'recent_transactions': recent_transactions}
    metrics: dict[str, object | None]
    focus_crop: str | None = None
    market_average_price = 0.0

    if current_user.user_type == UserType.FARMER:
        recent_listings_result = await db.execute(
            select(Listing)
            .where(Listing.farmer_id == current_user.id)
            .order_by(Listing.created_at.desc())
            .limit(4)
        )
        recent_listings = recent_listings_result.scalars().all()
        feed['recent_listings'] = [_listing_payload(listing) for listing in recent_listings]

        recent_orders_result = await db.execute(
            select(Order)
            .join(Listing, Order.listing_id == Listing.id)
            .where(Listing.farmer_id == current_user.id)
            .options(selectinload(Order.listing), selectinload(Order.buyer))
            .order_by(Order.created_at.desc())
            .limit(4)
        )
        recent_orders = recent_orders_result.scalars().unique().all()
        feed['recent_orders'] = [
            {
                'id': order.id,
                'status': order.status.value,
                'quantity_kg': decimal_to_float(order.quantity_kg),
                'total_amount': decimal_to_float(order.total_amount),
                'created_at': serialize_datetime(order.created_at),
                'dispatched_at': serialize_datetime(order.dispatched_at),
                'delivery_confirmed_at': serialize_datetime(order.delivery_confirmed_at),
                'listing': {
                    'id': order.listing.id,
                    'crop_name': order.listing.crop_name,
                    'market_type': order.listing.market_type.value,
                },
                'buyer': {
                    'id': order.buyer.id,
                    'name': order.buyer.name,
                    'village': order.buyer.village,
                },
            }
            for order in recent_orders
        ]

        active_listings_result = await db.execute(
            select(func.count(Listing.id), func.sum(Listing.quantity_remaining))
            .where(Listing.farmer_id == current_user.id, Listing.status.in_([ListingStatus.ACTIVE, ListingStatus.PARTIALLY_SOLD]))
        )
        active_listings, live_volume = active_listings_result.one()
        sold_volume_result = await db.execute(
            select(func.sum(Listing.quantity_kg - func.coalesce(Listing.quantity_remaining, Decimal('0.00'))))
            .where(Listing.farmer_id == current_user.id)
        )
        incoming_orders_result = await db.execute(
            select(func.count(Order.id), func.sum(Order.total_amount))
            .join(Listing, Order.listing_id == Listing.id)
            .where(Listing.farmer_id == current_user.id, Order.status.in_([OrderStatus.ESCROW_LOCKED, OrderStatus.IN_TRANSIT]))
        )
        incoming_orders, pending_value = incoming_orders_result.one()
        delivered_sales_result = await db.execute(
            select(func.count(Order.id), func.sum(Order.total_amount))
            .join(Listing, Order.listing_id == Listing.id)
            .where(Listing.farmer_id == current_user.id, Order.status == OrderStatus.DELIVERED)
        )
        delivered_orders, delivered_sales = delivered_sales_result.one()
        in_transit_result = await db.execute(
            select(func.count(Order.id))
            .join(Listing, Order.listing_id == Listing.id)
            .where(Listing.farmer_id == current_user.id, Order.status == OrderStatus.IN_TRANSIT)
        )
        expiring_result = await db.execute(
            select(Listing)
            .where(
                Listing.farmer_id == current_user.id,
                Listing.status.in_([ListingStatus.ACTIVE, ListingStatus.PARTIALLY_SOLD]),
                Listing.expires_at.is_not(None),
                Listing.expires_at <= datetime.now(timezone.utc) + timedelta(hours=24),
            )
            .order_by(Listing.expires_at.asc())
            .limit(2)
        )
        expiring_listings = expiring_result.scalars().all()

        metrics = {
            'role': 'farmer',
            'active_listings': int(active_listings or 0),
            'incoming_orders': int(incoming_orders or 0),
            'in_transit': int(in_transit_result.scalar_one() or 0),
            'delivered_orders': int(delivered_orders or 0),
            'live_volume_kg': round(float(live_volume or 0), 2),
            'sold_volume_kg': round(float(sold_volume_result.scalar_one() or 0), 2),
            'delivered_sales': round(float(delivered_sales or 0), 2),
            'pending_payout': round(float(pending_value or 0), 2),
        }

        for listing in expiring_listings:
            notifications.append(
                {
                    'id': f'expiring-{listing.id}',
                    'type': 'listing_expiry',
                    'title': f'{listing.crop_name.title()} listing expires soon',
                    'body': f'Listing {listing.id} will expire within 24 hours unless it sells first.',
                    'created_at': serialize_datetime(listing.expires_at),
                }
            )
        for order in recent_orders[:2]:
            notifications.append(
                {
                    'id': f'farmer-order-{order.id}',
                    'type': 'incoming_order',
                    'title': f'Order {order.id} needs attention',
                    'body': f'{order.buyer.name} placed {decimal_to_float(order.quantity_kg)}kg for {order.listing.crop_name}. Status: {order.status.value.replace("_", " ")}.',
                    'created_at': serialize_datetime(order.created_at),
                }
            )

        focus_crop = recent_listings[0].crop_name if recent_listings else None
    else:
        recent_orders_result = await db.execute(
            select(Order)
            .where(Order.buyer_id == current_user.id)
            .options(selectinload(Order.listing).selectinload(Listing.farmer))
            .order_by(Order.created_at.desc())
            .limit(4)
        )
        recent_orders = recent_orders_result.scalars().unique().all()
        feed['recent_orders'] = [
            {
                'id': order.id,
                'status': order.status.value,
                'quantity_kg': decimal_to_float(order.quantity_kg),
                'total_amount': decimal_to_float(order.total_amount),
                'created_at': serialize_datetime(order.created_at),
                'dispatched_at': serialize_datetime(order.dispatched_at),
                'delivery_confirmed_at': serialize_datetime(order.delivery_confirmed_at),
                'listing': {
                    'id': order.listing.id,
                    'crop_name': order.listing.crop_name,
                    'farmer_name': order.listing.farmer.name,
                    'market_type': order.listing.market_type.value,
                },
            }
            for order in recent_orders
        ]

        active_orders_result = await db.execute(
            select(func.count(Order.id), func.sum(Order.total_amount), func.sum(Order.quantity_kg))
            .where(Order.buyer_id == current_user.id, Order.status.in_([OrderStatus.ESCROW_LOCKED, OrderStatus.IN_TRANSIT]))
        )
        active_orders, outstanding_escrow, active_volume = active_orders_result.one()
        delivered_result = await db.execute(
            select(func.count(Order.id), func.sum(Order.total_amount), func.sum(Order.quantity_kg))
            .where(Order.buyer_id == current_user.id, Order.status == OrderStatus.DELIVERED)
        )
        delivered_orders, delivered_spend, delivered_volume = delivered_result.one()
        all_orders_result = await db.execute(
            select(func.count(Order.id), func.sum(Order.total_amount))
            .where(Order.buyer_id == current_user.id)
        )
        total_orders, total_spend = all_orders_result.one()

        metrics = {
            'role': 'buyer',
            'active_orders': int(active_orders or 0),
            'delivered_orders': int(delivered_orders or 0),
            'total_orders': int(total_orders or 0),
            'outstanding_escrow': round(float(outstanding_escrow or 0), 2),
            'total_spend': round(float(total_spend or 0), 2),
            'delivered_spend': round(float(delivered_spend or 0), 2),
            'active_volume_kg': round(float(active_volume or 0), 2),
            'delivered_volume_kg': round(float(delivered_volume or 0), 2),
        }

        for order in recent_orders[:3]:
            notifications.append(
                {
                    'id': f'buyer-order-{order.id}',
                    'type': 'order_update',
                    'title': f'{order.listing.crop_name.title()} order update',
                    'body': f'Order {order.id} from {order.listing.farmer.name} is currently {order.status.value.replace("_", " ")}.',
                    'created_at': serialize_datetime(order.delivery_confirmed_at or order.dispatched_at or order.created_at),
                }
            )

        focus_crop = recent_orders[0].listing.crop_name if recent_orders else None

    if decimal_to_float(wallet.balance) is not None and float(wallet.balance) < 300:
        notifications.append(
            {
                'id': 'wallet-low-balance',
                'type': 'wallet_alert',
                'title': 'Wallet balance is running low',
                'body': 'Top up your wallet to avoid failed checkout or payout actions.',
                'created_at': serialize_datetime(datetime.now(timezone.utc)),
            }
        )

    if focus_crop:
        market_average_result = await db.execute(
            select(func.avg(Listing.price_per_kg))
            .where(Listing.status.in_([ListingStatus.ACTIVE, ListingStatus.PARTIALLY_SOLD]), Listing.crop_name == focus_crop)
        )
        market_average_price = round(float(market_average_result.scalar_one() or 0), 2)

    price_guidance = None
    if focus_crop:
        mandi_reference_price = round(float(await get_mandi_price(focus_crop)), 2)
        price_guidance = {
            'crop_name': focus_crop,
            'mandi_reference_price': mandi_reference_price,
            'live_market_average': market_average_price,
            'recommended_band': {
                'min': round(mandi_reference_price * 0.9, 2),
                'max': round(mandi_reference_price * 1.1, 2),
            },
        }

    return envelope(
        {
            'profile': {
                'id': current_user.id,
                'name': current_user.name,
                'phone': current_user.phone,
                'village': current_user.village,
                'user_type': current_user.user_type.value,
                'language': current_user.language,
                'market_type': current_user.market_type.value,
                'reputation_score': float(current_user.reputation_score),
                'created_at': serialize_datetime(current_user.created_at),
            },
            'wallet': {
                'balance': decimal_to_float(wallet.balance),
                'locked_balance': decimal_to_float(wallet.locked_balance),
                'currency': wallet.currency,
            },
            'metrics': metrics,
            'feed': feed,
            'notifications': notifications[:6],
            'price_guidance': price_guidance,
        }
    )


@router.get('/profile')
async def profile(current_user: User = Depends(get_current_user)) -> dict[str, object | None]:
    return envelope(
        {
            'id': current_user.id,
            'name': current_user.name,
            'phone': current_user.phone,
            'village': current_user.village,
            'user_type': current_user.user_type.value,
            'language': current_user.language,
            'market_type': current_user.market_type.value,
            'reputation_score': float(current_user.reputation_score),
            'created_at': serialize_datetime(current_user.created_at),
        }
    )


@router.patch('/profile')
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    if payload.name is not None:
        valid, cleaned = validate_name(payload.name)
        if not valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=cleaned)
        current_user.name = cleaned
    if payload.village is not None:
        current_user.village = payload.village
    if payload.language is not None:
        current_user.language = payload.language
    await db.commit()
    await db.refresh(current_user)
    return await profile(current_user)


@router.get('/transactions')
async def transactions(
    tx_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    query: Select[tuple[Transaction]] = select(Transaction).where(Transaction.user_id == current_user.id)
    count_query = select(func.count(Transaction.id)).where(Transaction.user_id == current_user.id)
    if tx_type:
        try:
            tx_enum = TransactionType(tx_type)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unknown transaction type filter.') from exc
        query = query.where(Transaction.type == tx_enum)
        count_query = count_query.where(Transaction.type == tx_enum)
    if date_from is not None:
        query = query.where(Transaction.created_at >= date_from)
        count_query = count_query.where(Transaction.created_at >= date_from)
    if date_to is not None:
        query = query.where(Transaction.created_at <= date_to)
        count_query = count_query.where(Transaction.created_at <= date_to)
    query = query.order_by(Transaction.block_height.desc().nulls_last(), Transaction.created_at.desc(), Transaction.id.desc()).offset(offset).limit(limit)
    total = int((await db.execute(count_query)).scalar_one())
    result = await db.execute(query)
    items = [
        {
            'id': tx.id,
            'type': tx.type.value,
            'amount': decimal_to_float(tx.amount),
            'balance_after': decimal_to_float(tx.balance_after),
            'reference_id': tx.reference_id,
            'description': tx.description,
            'created_at': serialize_datetime(tx.created_at),
        }
        for tx in result.scalars().all()
    ]
    return envelope({'items': items, 'limit': limit, 'offset': offset, 'total': total, 'has_more': offset + limit < total})


@router.get('/listings')
async def my_listings(
    status_filter: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    if current_user.user_type != UserType.FARMER:
        return envelope({'items': [], 'total': 0, 'limit': limit, 'offset': offset, 'has_more': False})

    query = select(Listing).where(Listing.farmer_id == current_user.id)
    count_query = select(func.count(Listing.id)).where(Listing.farmer_id == current_user.id)
    if status_filter:
        try:
            status_enum = ListingStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unknown listing status filter.') from exc
        query = query.where(Listing.status == status_enum)
        count_query = count_query.where(Listing.status == status_enum)
    if search:
        search_term = f"%{search.strip().lower()}%"
        query = query.where(func.lower(Listing.crop_name).like(search_term))
        count_query = count_query.where(func.lower(Listing.crop_name).like(search_term))

    total = int((await db.execute(count_query)).scalar_one())
    result = await db.execute(query.order_by(Listing.created_at.desc()).offset(offset).limit(limit))
    items = [_listing_payload(listing) for listing in result.scalars().all()]
    return envelope({'items': items, 'total': total, 'limit': limit, 'offset': offset, 'has_more': offset + limit < total})


@router.post('/listings')
async def create_listing(
    payload: ListingCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    if current_user.user_type != UserType.FARMER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only farmers can create listings from the dashboard.')

    try:
        listing_market = _resolve_listing_market(current_user, payload.market_type)
        pickup_type = PickupType(payload.pickup_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid market type or pickup type.') from exc

    created_at = datetime.now(timezone.utc)
    price_inr = Decimal(str(payload.price_per_kg)).quantize(Decimal('0.01'))
    quantity = Decimal(str(payload.quantity_kg)).quantize(Decimal('0.01'))
    stored_price = inr_to_usd(price_inr) if listing_market == ListingMarketType.GLOBAL else price_inr
    currency = 'USD' if listing_market == ListingMarketType.GLOBAL else 'INR'

    listing = Listing(
        id=await generate_listing_id(db),
        farmer_id=current_user.id,
        crop_name=payload.crop_name,
        quantity_kg=quantity,
        quantity_remaining=quantity,
        price_per_kg=stored_price,
        currency=currency,
        market_type=listing_market,
        pickup_type=pickup_type,
        gi_tag=payload.gi_tag,
        organic_certified=bool(payload.organic_certified),
        created_at=created_at,
        blockchain_hash=hash_listing(
            {
                'farmer_id': current_user.id,
                'crop_name': payload.crop_name,
                'quantity_kg': quantity,
                'price_per_kg': stored_price,
                'currency': currency,
                'market_type': listing_market.value,
                'pickup_type': pickup_type.value,
                'gi_tag': payload.gi_tag,
                'organic_certified': bool(payload.organic_certified),
                'created_at': created_at,
            }
        ),
    )
    db.add(listing)
    await db.flush()
    listing.qr_code_path = generate_listing_qr(listing, current_user)
    await anchor_listing_on_chain(db, listing=listing, farmer=current_user)
    await db.commit()
    await db.refresh(listing)

    await send_notification(
        current_user.phone,
        'listing_created',
        {'crop': payload.crop_name.title(), 'listing_id': listing.id},
        current_user.language,
    )

    return envelope(_listing_payload(listing))


@router.patch('/listings/{listing_id}')
async def patch_listing(
    listing_id: str,
    payload: ListingUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    if current_user.user_type != UserType.FARMER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only farmers can update listings.')
    if all(value is None for value in payload.model_dump().values()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Submit at least one listing field to update.')

    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Listing not found.')

    try:
        listing = await update_listing(
            db,
            listing=listing,
            farmer=current_user,
            quantity_kg=payload.quantity_kg,
            price_per_kg=payload.price_per_kg,
            pickup_type=payload.pickup_type,
            gi_tag=payload.gi_tag,
            organic_certified=payload.organic_certified,
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(listing)
    return envelope({'message': f'Listing {listing.id} updated successfully.', 'listing': _listing_payload(listing)})


@router.post('/listings/{listing_id}/cancel')
async def cancel_dashboard_listing(
    listing_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    if current_user.user_type != UserType.FARMER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only farmers can cancel listings.')

    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Listing not found.')

    try:
        await cancel_listing(db, listing=listing, farmer=current_user)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await db.commit()
    return envelope({'message': f'Listing {listing.id} cancelled.', 'listing': _listing_payload(listing)})


@router.get('/orders')
async def my_orders(
    status_filter: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    query = (
        select(Order)
        .where(Order.buyer_id == current_user.id)
        .options(selectinload(Order.listing).selectinload(Listing.farmer))
    )
    count_query = select(func.count(Order.id)).where(Order.buyer_id == current_user.id)
    if status_filter:
        try:
            status_enum = OrderStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unknown order status filter.') from exc
        query = query.where(Order.status == status_enum)
        count_query = count_query.where(Order.status == status_enum)
    if search:
        search_term = f"%{search.strip().lower()}%"
        query = query.join(Listing, Order.listing_id == Listing.id).where(func.lower(Listing.crop_name).like(search_term))
        count_query = count_query.join(Listing, Order.listing_id == Listing.id).where(func.lower(Listing.crop_name).like(search_term))

    total = int((await db.execute(count_query)).scalar_one())
    result = await db.execute(query.order_by(Order.created_at.desc()).offset(offset).limit(limit))
    items = [
        {
            'id': order.id,
            'status': order.status.value,
            'quantity_kg': decimal_to_float(order.quantity_kg),
            'total_amount': decimal_to_float(order.total_amount),
            'platform_fee': decimal_to_float(order.platform_fee),
            'dispatched_at': serialize_datetime(order.dispatched_at),
            'delivery_confirmed_at': serialize_datetime(order.delivery_confirmed_at),
            'created_at': serialize_datetime(order.created_at),
            'listing': {
                'id': order.listing.id,
                'crop_name': order.listing.crop_name,
                'farmer_name': order.listing.farmer.name,
            },
            'delivery_code': build_release_key(order.listing, order),
        }
        for order in result.scalars().unique().all()
    ]
    return envelope({'items': items, 'total': total, 'limit': limit, 'offset': offset, 'has_more': offset + limit < total})


@router.get('/incoming-orders')
async def incoming_orders(
    status_filter: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    if current_user.user_type != UserType.FARMER:
        return envelope({'items': [], 'total': 0, 'limit': limit, 'offset': offset, 'has_more': False})

    query = (
        select(Order)
        .join(Listing, Order.listing_id == Listing.id)
        .where(Listing.farmer_id == current_user.id)
        .options(selectinload(Order.listing), selectinload(Order.buyer))
    )
    count_query = select(func.count(Order.id)).join(Listing, Order.listing_id == Listing.id).where(Listing.farmer_id == current_user.id)

    if status_filter:
        try:
            status_enum = OrderStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unknown incoming order status filter.') from exc
        query = query.where(Order.status == status_enum)
        count_query = count_query.where(Order.status == status_enum)
    if search:
        search_term = f"%{search.strip().lower()}%"
        filter_clause = or_(
            func.lower(Listing.crop_name).like(search_term),
            func.lower(User.name).like(search_term),
            func.lower(func.coalesce(User.village, '')).like(search_term),
        )
        query = query.join(User, Order.buyer_id == User.id).where(filter_clause)
        count_query = count_query.join(User, Order.buyer_id == User.id).where(filter_clause)

    total = int((await db.execute(count_query)).scalar_one())
    result = await db.execute(query.order_by(Order.created_at.desc()).offset(offset).limit(limit))
    items = [
        {
            'id': order.id,
            'status': order.status.value,
            'quantity_kg': decimal_to_float(order.quantity_kg),
            'total_amount': decimal_to_float(order.total_amount),
            'created_at': serialize_datetime(order.created_at),
            'dispatched_at': serialize_datetime(order.dispatched_at),
            'delivery_confirmed_at': serialize_datetime(order.delivery_confirmed_at),
            'listing': {
                'id': order.listing.id,
                'crop_name': order.listing.crop_name,
                'status': order.listing.status.value,
            },
            'buyer': {
                'id': order.buyer.id,
                'name': order.buyer.name,
                'village': order.buyer.village,
            },
            'delivery_code': build_release_key(order.listing, order),
            'release_key': build_release_key(order.listing, order),
        }
        for order in result.scalars().unique().all()
    ]
    return envelope({'items': items, 'total': total, 'limit': limit, 'offset': offset, 'has_more': offset + limit < total})


@router.post('/orders/{order_id}/dispatch')
async def dispatch_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    if current_user.user_type != UserType.FARMER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only farmers can dispatch orders.')

    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.listing).selectinload(Listing.farmer), selectinload(Order.buyer))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found.')

    try:
        await mark_order_in_transit(db, order=order, farmer=current_user)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await db.commit()
    return envelope({'message': f'Order {order.id} marked as dispatched.', 'order_id': order.id, 'status': order.status.value, 'dispatched_at': serialize_datetime(order.dispatched_at)})


@router.post('/orders/{order_id}/confirm')
async def confirm_dashboard_order(
    order_id: str,
    payload: OrderConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    result = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.listing).selectinload(Listing.farmer), selectinload(Order.buyer))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found.')
    try:
        await confirm_order_delivery(db, order=order, buyer=current_user, release_key=payload.release_key)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    return envelope({'message': f'Order {order.id} confirmed successfully.', 'order_id': order.id, 'status': order.status.value})














