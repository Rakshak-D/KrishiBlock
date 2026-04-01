from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.models.listing import Listing
from app.models.order import Order
from app.models.transaction import Transaction
from app.services.blockchain_sim import chain_transaction, get_genesis_hash, verify_chain
from app.utils.serializers import decimal_to_float, envelope, serialize_datetime


router = APIRouter(prefix='/api/ledger', tags=['ledger'])
settings = get_settings()


def _normalized_payload(transaction: Transaction) -> dict[str, object | None]:
    return {
        'id': transaction.id,
        'user_id': transaction.user_id,
        'type': transaction.type.value,
        'amount': transaction.amount,
        'balance_after': transaction.balance_after,
        'reference_id': transaction.reference_id,
        'description': transaction.description,
        'created_at': transaction.created_at,
    }


@router.get('')
async def public_ledger(
    limit: int = Query(default=12, ge=3, le=50),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    transactions_result = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.user))
        .order_by(Transaction.created_at.asc(), Transaction.id.asc())
    )
    transactions = transactions_result.scalars().all()

    order_ids = [tx.reference_id for tx in transactions if tx.reference_id and tx.reference_id.startswith('ORD')]
    listing_ids = [tx.reference_id for tx in transactions if tx.reference_id and tx.reference_id.startswith('LST')]

    orders_by_id: dict[str, Order] = {}
    if order_ids:
        orders_result = await db.execute(
            select(Order)
            .where(Order.id.in_(order_ids))
            .options(selectinload(Order.listing), selectinload(Order.buyer))
        )
        orders_by_id = {order.id: order for order in orders_result.scalars().unique().all()}

    if orders_by_id:
        listing_ids.extend([order.listing_id for order in orders_by_id.values() if order.listing_id])

    listing_anchors_result = await db.execute(
        select(Listing)
        .options(selectinload(Listing.farmer))
        .order_by(Listing.created_at.desc(), Listing.id.desc())
        .limit(6)
    )
    anchor_listings = listing_anchors_result.scalars().unique().all()
    listings_by_id = {listing.id: listing for listing in anchor_listings}

    if listing_ids:
        referenced_listings_result = await db.execute(
            select(Listing)
            .where(Listing.id.in_(set(listing_ids)))
            .options(selectinload(Listing.farmer))
        )
        listings_by_id.update({listing.id: listing for listing in referenced_listings_result.scalars().unique().all()})

    blocks: list[dict[str, object | None]] = []
    previous_hash = get_genesis_hash()
    for index, transaction in enumerate(transactions, start=1):
        expected_hash = chain_transaction(previous_hash, _normalized_payload(transaction))
        reference_listing = listings_by_id.get(transaction.reference_id or '')
        reference_order = orders_by_id.get(transaction.reference_id or '')
        linked_listing = reference_listing or (reference_order.listing if reference_order is not None else None)
        actor_name = transaction.user.name if transaction.user is not None else 'AgriChain system'
        blocks.append(
            {
                'block_number': index,
                'transaction_id': transaction.id,
                'previous_hash': previous_hash,
                'current_hash': transaction.hash,
                'expected_hash': expected_hash,
                'verified': transaction.hash == expected_hash,
                'type': transaction.type.value,
                'actor_name': actor_name,
                'actor_role': transaction.user.user_type.value if transaction.user is not None else 'system',
                'reference_id': transaction.reference_id,
                'linked_listing_id': linked_listing.id if linked_listing is not None else None,
                'linked_crop_name': linked_listing.crop_name if linked_listing is not None else None,
                'amount': decimal_to_float(transaction.amount),
                'description': transaction.description,
                'created_at': serialize_datetime(transaction.created_at),
            }
        )
        previous_hash = transaction.hash

    totals_result = await db.execute(
        select(
            func.count(Transaction.id),
            func.count(Listing.id),
            func.count(func.distinct(Order.id)),
        )
        .select_from(Transaction)
        .join(Order, Transaction.reference_id == Order.id, isouter=True)
        .join(Listing, Listing.id == Transaction.reference_id, isouter=True)
    )
    total_blocks, listing_hashes_from_transactions, linked_orders = totals_result.one()

    anchors = [
        {
            'listing_id': listing.id,
            'crop_name': listing.crop_name,
            'farmer_name': listing.farmer.name,
            'market_type': listing.market_type.value,
            'status': listing.status.value,
            'created_at': serialize_datetime(listing.created_at),
            'listing_hash': listing.blockchain_hash,
            'verify_url': f'{settings.public_verify_url_base}/verify/{listing.id}',
        }
        for listing in anchor_listings
    ]

    normalized_transactions = [
        {
            **_normalized_payload(transaction),
            'hash': transaction.hash,
        }
        for transaction in transactions
    ]

    summary = {
        'chain_verified': verify_chain(normalized_transactions),
        'genesis_hash': get_genesis_hash(),
        'total_blocks': int(total_blocks or 0),
        'listing_anchors': len(anchors),
        'orders_tracked': int(linked_orders or 0),
        'ledger_events': int(total_blocks or 0),
        'latest_block_hash': blocks[-1]['current_hash'] if blocks else None,
        'latest_block_at': blocks[-1]['created_at'] if blocks else None,
    }

    return envelope({'summary': summary, 'blocks': list(reversed(blocks[-limit:])), 'anchors': anchors})


