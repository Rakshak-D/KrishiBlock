from __future__ import annotations

from datetime import datetime
from decimal import Decimal


def envelope(data: object = None, error: str | None = None, success: bool = True) -> dict[str, object | None]:
    return {'success': success, 'data': data, 'error': error}


def decimal_to_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
