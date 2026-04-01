from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Mapping


def _serialize_value(value: object) -> str:
    if isinstance(value, Decimal):
        return f'{value:.2f}'
    if isinstance(value, datetime):
        normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return normalized.isoformat()
    return str(value)


def get_genesis_hash() -> str:
    return hashlib.sha256('agrichain_genesis'.encode('utf-8')).hexdigest()


def hash_listing(data: Mapping[str, object]) -> str:
    payload = json.dumps(dict(data), sort_keys=True, default=_serialize_value)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def chain_transaction(prev_hash: str, tx_data: Mapping[str, object]) -> str:
    payload = prev_hash + json.dumps(dict(tx_data), sort_keys=True, default=_serialize_value)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def _transaction_payload(transaction: Mapping[str, object]) -> dict[str, object]:
    return {
        'id': transaction.get('id'),
        'user_id': transaction.get('user_id'),
        'type': transaction.get('type'),
        'amount': transaction.get('amount'),
        'balance_after': transaction.get('balance_after'),
        'reference_id': transaction.get('reference_id'),
        'description': transaction.get('description'),
        'created_at': transaction.get('created_at'),
    }


def verify_chain(transactions: list[Mapping[str, object]]) -> bool:
    if not transactions:
        return True

    previous_hash = get_genesis_hash()
    ordered = sorted(transactions, key=lambda item: (str(item.get('created_at') or ''), str(item.get('id') or '')))
    for transaction in ordered:
        expected = chain_transaction(previous_hash, _transaction_payload(transaction))
        if str(transaction.get('hash') or '') != expected:
            return False
        previous_hash = str(transaction.get('hash'))
    return True
