from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from app.config import get_settings
from app.models.listing import Listing, ListingStatus
from app.models.order import Order
from app.models.transaction import Transaction
from app.services.blockchain_sim import verify_chain
from app.utils.serializers import decimal_to_float, serialize_datetime


settings = get_settings()


def _decimal_text(value: Decimal | None) -> str:
    normalized = value or Decimal('0.00')
    return f'{normalized:.2f}'


def _sorted_orders(listing: Listing) -> list[Order]:
    return sorted(list(listing.orders or []), key=lambda order: (order.created_at or '', order.id or ''))


def _normalized_transactions(transactions: Iterable[Transaction]) -> list[dict[str, object]]:
    return [
        {
            'id': tx.id,
            'user_id': tx.user_id,
            'type': tx.type.value,
            'amount': tx.amount,
            'balance_after': tx.balance_after,
            'reference_id': tx.reference_id,
            'description': tx.description,
            'created_at': tx.created_at,
            'hash': tx.hash,
        }
        for tx in transactions
    ]


def build_listing_timeline(listing: Listing) -> list[dict[str, str | None]]:
    orders = _sorted_orders(listing)
    first_order = orders[0] if orders else None
    latest_dispatch = max((order.dispatched_at for order in orders if order.dispatched_at), default=None)
    latest_delivery = max((order.delivery_confirmed_at for order in orders if order.delivery_confirmed_at), default=None)

    timeline = [
        {'label': 'Listed', 'timestamp': serialize_datetime(listing.created_at)},
        {'label': 'Escrow locked', 'timestamp': serialize_datetime(first_order.created_at if first_order else None)},
        {'label': 'Dispatched', 'timestamp': serialize_datetime(latest_dispatch)},
        {'label': 'Delivered', 'timestamp': serialize_datetime(latest_delivery)},
    ]
    if listing.status == ListingStatus.CANCELLED:
        timeline.append({'label': 'Cancelled', 'timestamp': serialize_datetime(latest_delivery or listing.created_at)})
    if listing.status == ListingStatus.EXPIRED:
        timeline.append({'label': 'Expired', 'timestamp': serialize_datetime(listing.expires_at)})
    return timeline


def build_supply_flow(listing: Listing) -> list[dict[str, str | int | None]]:
    events: list[dict[str, str | int | None]] = [
        {
            'stage': 'listed',
            'label': 'Listing published',
            'actor': listing.farmer.name if listing.farmer else 'Farmer',
            'detail': f'{listing.crop_name.title()} listing published with {_decimal_text(listing.quantity_kg)}kg ready for sale.',
            'timestamp': serialize_datetime(listing.created_at),
            'status': 'complete',
            'order_index': None,
        }
    ]

    for index, order in enumerate(_sorted_orders(listing), start=1):
        buyer_label = f'Buyer order {index}'
        events.append(
            {
                'stage': 'escrow_locked',
                'label': 'Escrow secured',
                'actor': buyer_label,
                'detail': f'{_decimal_text(order.quantity_kg)}kg reserved and payment of {_decimal_text(order.total_amount)} locked in escrow.',
                'timestamp': serialize_datetime(order.created_at),
                'status': 'complete',
                'order_index': index,
            }
        )
        if order.dispatched_at:
            events.append(
                {
                    'stage': 'in_transit',
                    'label': 'Dispatch recorded',
                    'actor': listing.farmer.name if listing.farmer else 'Farmer',
                    'detail': f'Farmer marked order {order.id} as dispatched to the buyer.',
                    'timestamp': serialize_datetime(order.dispatched_at),
                    'status': 'complete',
                    'order_index': index,
                }
            )
        if order.delivery_confirmed_at:
            events.append(
                {
                    'stage': 'delivered',
                    'label': 'Delivery confirmed',
                    'actor': buyer_label,
                    'detail': f'Buyer confirmed receipt and escrow for order {order.id} was released.',
                    'timestamp': serialize_datetime(order.delivery_confirmed_at),
                    'status': 'complete',
                    'order_index': index,
                }
            )

    if listing.status == ListingStatus.CANCELLED:
        events.append(
            {
                'stage': 'cancelled',
                'label': 'Listing cancelled',
                'actor': listing.farmer.name if listing.farmer else 'Farmer',
                'detail': 'The farmer cancelled this listing after closing active sale windows.',
                'timestamp': serialize_datetime(listing.expires_at or listing.created_at),
                'status': 'complete',
                'order_index': None,
            }
        )
    elif listing.status == ListingStatus.EXPIRED:
        events.append(
            {
                'stage': 'expired',
                'label': 'Listing expired',
                'actor': 'System',
                'detail': 'The listing expired after the availability window closed.',
                'timestamp': serialize_datetime(listing.expires_at),
                'status': 'complete',
                'order_index': None,
            }
        )
    return events


def build_transaction_trail(listing: Listing, transactions: Iterable[Transaction]) -> list[dict[str, object | None]]:
    orders = {order.id: order for order in _sorted_orders(listing)}
    order_buyer_ids = {order.buyer_id for order in orders.values()}
    trail: list[dict[str, object | None]] = []
    for tx in transactions:
        actor = 'Platform ledger'
        if tx.user_id == listing.farmer_id:
            actor = listing.farmer.name if listing.farmer else 'Farmer wallet'
        elif tx.user_id in order_buyer_ids:
            actor = 'Buyer wallet'
        trail.append(
            {
                'id': tx.id,
                'actor': actor,
                'type': tx.type.value,
                'amount': decimal_to_float(tx.amount),
                'reference_id': tx.reference_id,
                'description': tx.description,
                'created_at': serialize_datetime(tx.created_at),
                'hash': tx.hash,
            }
        )
    return trail


def build_transparency_payload(listing: Listing, transactions: list[Transaction]) -> dict[str, object | None]:
    normalized = _normalized_transactions(transactions)
    reference_ids = sorted({reference_id for reference_id in [listing.id, *[order.id for order in listing.orders], *[tx.reference_id for tx in transactions if tx.reference_id]] if reference_id})
    return {
        'listing_hash': listing.blockchain_hash,
        'blockchain_verified': verify_chain(normalized),
        'order_count': len(listing.orders),
        'transaction_count': len(transactions),
        'latest_transaction_hash': transactions[-1].hash if transactions else None,
        'reference_ids': reference_ids,
        'verify_url': f'{settings.public_verify_url_base}/verify/{listing.id}',
    }
