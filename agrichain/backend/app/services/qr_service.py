from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import qrcode

from app.config import get_settings


if TYPE_CHECKING:
    from app.models.listing import Listing
    from app.models.order import Order
    from app.models.user import User


settings = get_settings()


def inr_to_usd(value: Decimal) -> Decimal:
    return (Decimal(value) / settings.USD_EXCHANGE_RATE).quantize(Decimal('0.01'))


def build_verify_url(listing_id: str) -> str:
    return f'{settings.public_verify_url_base}/verify/{listing_id}'


def generate_listing_qr(listing: 'Listing', farmer: 'User') -> str:
    settings.qr_dir.mkdir(parents=True, exist_ok=True)
    verify_url = build_verify_url(listing.id)

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(verify_url)
    qr.make(fit=True)

    image = qr.make_image(fill_color='#2D5016', back_color='white')
    path = settings.qr_dir / f'{listing.id}.png'
    image.save(path)
    return f'static/qr/{listing.id}.png'


def build_dpp(listing: 'Listing', farmer: 'User', orders: list['Order']) -> dict[str, object]:
    if listing.currency == 'INR':
        usd_equivalent = float(inr_to_usd(listing.price_per_kg))
    else:
        usd_equivalent = float(listing.price_per_kg)

    return {
        'listing_id': listing.id,
        'farmer': {
            'name': farmer.name,
            'village': farmer.village,
            'id': farmer.id,
            'rating': float(farmer.reputation_score),
        },
        'product': {
            'crop': listing.crop_name,
            'qty_kg': float(listing.quantity_kg),
            'price_per_kg': float(listing.price_per_kg),
            'currency': listing.currency,
            'usd_equivalent': usd_equivalent,
            'organic': bool(listing.organic_certified),
            'gi_tag': listing.gi_tag,
        },
        'market': listing.market_type.value,
        'supply_chain': [
            {
                'event': order.status.value,
                'timestamp': order.delivery_confirmed_at.isoformat() if order.delivery_confirmed_at else order.dispatched_at.isoformat() if order.dispatched_at else order.created_at.isoformat() if order.created_at else None,
            }
            for order in orders
        ],
        'blockchain_hash': listing.blockchain_hash,
        'verified': True,
        'verify_url': build_verify_url(listing.id),
    }

