from __future__ import annotations

import hashlib

from app.models.listing import Listing
from app.models.order import Order


KEY_LENGTH = 10


def build_release_key(listing: Listing, order: Order) -> str:
    seed = f"{listing.blockchain_hash}:{order.id}:{order.buyer_id}"
    return hashlib.sha256(seed.encode('utf-8')).hexdigest()[:KEY_LENGTH].upper()


def validate_release_key(listing: Listing, order: Order, submitted_key: str) -> bool:
    expected = build_release_key(listing, order)
    return expected == submitted_key.strip().upper()


def mask_release_key(key: str) -> str:
    normalized = key.strip().upper()
    if len(normalized) <= 4:
        return normalized
    return f"{'*' * (len(normalized) - 4)}{normalized[-4:]}"
