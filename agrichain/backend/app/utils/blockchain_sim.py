from __future__ import annotations

from typing import Mapping

from app.services.blockchain_sim import (
    build_transaction_payload,
    calculate_merkle_root,
    derive_wallet_address,
    generate_wallet_identity,
    get_genesis_hash,
    hash_listing,
    hash_transaction_payload,
    mine_block,
    sign_transaction_payload,
    verify_chain,
    verify_signature,
)


def create_listing_hash(listing_data: Mapping[str, object]) -> str:
    return hash_listing(listing_data)


def create_transaction_hash(tx_data: Mapping[str, object]) -> str:
    return hash_transaction_payload(tx_data)


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
                'transaction_hash': getattr(transaction, 'transaction_hash', None),
                'previous_hash': getattr(transaction, 'previous_hash', None),
                'merkle_root': getattr(transaction, 'merkle_root', None),
                'signature': getattr(transaction, 'signature', None),
                'signer_public_key': getattr(transaction, 'signer_public_key', None),
                'signer_address': getattr(transaction, 'signer_address', None),
                'block_height': getattr(transaction, 'block_height', None),
                'difficulty': getattr(transaction, 'difficulty', None),
                'nonce': getattr(transaction, 'nonce', None),
            }
        )
    return verify_chain(normalized)


__all__ = [
    'build_transaction_payload',
    'calculate_merkle_root',
    'create_listing_hash',
    'create_transaction_hash',
    'derive_wallet_address',
    'generate_wallet_identity',
    'get_genesis_hash',
    'mine_block',
    'sign_transaction_payload',
    'verify_chain',
    'verify_signature',
    'verify_transaction_chain',
]
