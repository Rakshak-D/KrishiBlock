from __future__ import annotations

from typing import Mapping

from app.services.blockchain_sim import chain_transaction, get_genesis_hash, hash_listing, verify_chain


def create_listing_hash(listing_data: Mapping[str, object]) -> str:
    return hash_listing(listing_data)


def create_transaction_hash(prev_hash: str, tx_data: Mapping[str, object]) -> str:
    return chain_transaction(prev_hash, tx_data)


def verify_transaction_chain(transactions: list[object]) -> bool:
    normalized: list[dict[str, object]] = []
    for transaction in transactions:
        normalized.append(
            {
                'id': getattr(transaction, 'id', None),
                'user_id': getattr(transaction, 'user_id', None),
                'type': getattr(getattr(transaction, 'type', None), 'value', getattr(transaction, 'type', None)),
                'amount': getattr(transaction, 'amount', None),
                'balance_after': getattr(transaction, 'balance_after', None),
                'reference_id': getattr(transaction, 'reference_id', None),
                'description': getattr(transaction, 'description', None),
                'created_at': getattr(transaction, 'created_at', None),
                'hash': getattr(transaction, 'hash', None),
            }
        )
    return verify_chain(normalized)


__all__ = ['create_listing_hash', 'create_transaction_hash', 'verify_transaction_chain', 'get_genesis_hash']
