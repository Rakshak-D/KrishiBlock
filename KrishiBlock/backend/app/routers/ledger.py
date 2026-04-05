from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.models.listing import Listing
from app.models.order import Order
from app.models.transaction import Transaction
from app.services.blockchain_sim import block_confirmations, verify_chain
from app.services.session import _get_json
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
        'hash': transaction.hash,
        'transaction_hash': transaction.transaction_hash,
        'previous_hash': transaction.previous_hash,
        'merkle_root': transaction.merkle_root,
        'signature': transaction.signature,
        'signer_public_key': transaction.signer_public_key,
        'signer_address': transaction.signer_address,
        'block_height': transaction.block_height,
        'difficulty': transaction.difficulty,
        'nonce': transaction.nonce,
    }


@router.get('')
async def public_ledger(
    limit: int = Query(default=12, ge=3, le=50),
    search: str | None = Query(default=None, max_length=120),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    transactions_result = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.user))
        .order_by(Transaction.block_height.asc().nulls_last(), Transaction.created_at.asc(), Transaction.id.asc())
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

    chain_entries = [_normalized_payload(transaction) for transaction in transactions]
    chain_verified = verify_chain(chain_entries)
    current_height = max((int(tx.block_height or 0) for tx in transactions), default=0)
    average_hash_rate = round(sum(float(tx.hash_rate_hps or 0) for tx in transactions) / max(len(transactions), 1), 2) if transactions else 0.0

    blocks: list[dict[str, object | None]] = []
    for transaction in transactions:
        reference_listing = listings_by_id.get(transaction.reference_id or '')
        reference_order = orders_by_id.get(transaction.reference_id or '')
        linked_listing = reference_listing or (reference_order.listing if reference_order is not None else None)
        actor_name = transaction.user.name if transaction.user is not None else 'KrishiBlock'
        blocks.append(
            {
                'block_number': transaction.block_height,
                'transaction_id': transaction.id,
                'transaction_hash': transaction.transaction_hash,
                'previous_hash': transaction.previous_hash,
                'current_hash': transaction.hash,
                'merkle_root': transaction.merkle_root,
                'verified': chain_verified,
                'type': transaction.type.value,
                'actor_name': actor_name,
                'actor_role': transaction.user.user_type.value if transaction.user is not None else 'system',
                'signer_address': transaction.signer_address,
                'reference_id': transaction.reference_id,
                'linked_listing_id': linked_listing.id if linked_listing is not None else None,
                'linked_crop_name': linked_listing.crop_name if linked_listing is not None else None,
                'amount': decimal_to_float(transaction.amount),
                'description': transaction.description,
                'created_at': serialize_datetime(transaction.created_at),
                'difficulty': transaction.difficulty,
                'nonce': transaction.nonce,
                'hash_rate_hps': transaction.hash_rate_hps,
                'confirmations': block_confirmations(int(transaction.block_height or 0), current_height) if transaction.block_height else 0,
            }
        )

    if search:
        needle = search.strip().lower()
        blocks = [
            block for block in blocks
            if needle in str(block.get('transaction_id') or '').lower()
            or needle in str(block.get('reference_id') or '').lower()
            or needle in str(block.get('current_hash') or '').lower()
            or needle in str(block.get('signer_address') or '').lower()
            or needle in str(block.get('linked_crop_name') or '').lower()
        ]

    totals_result = await db.execute(
        select(
            func.count(Transaction.id),
            func.count(func.distinct(Transaction.signer_address)),
            func.count(func.distinct(Order.id)),
        )
        .select_from(Transaction)
        .join(Order, Transaction.reference_id == Order.id, isouter=True)
    )
    total_blocks, total_addresses, linked_orders = totals_result.one()

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

    mempool_payload = await _get_json('mempool:pending')
    pending_count = len(mempool_payload) if isinstance(mempool_payload, list) else 0

    summary = {
        'chain_verified': chain_verified,
        'genesis_hash': transactions[0].previous_hash if transactions else None,
        'total_blocks': int(total_blocks or 0),
        'total_transactions': int(total_blocks or 0),
        'listing_anchors': len(anchors),
        'orders_tracked': int(linked_orders or 0),
        'active_addresses': int(total_addresses or 0),
        'mempool_pending': pending_count,
        'difficulty': int(transactions[-1].difficulty or 0) if transactions else 0,
        'average_hash_rate_hps': average_hash_rate,
        'latest_block_hash': blocks[-1]['current_hash'] if blocks else None,
        'latest_block_at': blocks[-1]['created_at'] if blocks else None,
    }

    return envelope({'summary': summary, 'blocks': list(reversed(blocks[-limit:])), 'anchors': anchors})
