from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation


UPI_PATTERN = re.compile(r'^(?:[a-zA-Z0-9._-]+@[a-zA-Z]+|\d{10}@[a-zA-Z]+)$')


def _parse_decimal(text: str) -> Decimal | None:
    try:
        normalized = str(text or '').strip().replace(',', '')
        return Decimal(normalized)
    except (InvalidOperation, AttributeError):
        return None


def validate_quantity(text: str) -> tuple[bool, float, str]:
    value = _parse_decimal(text)
    if value is None:
        return False, 0.0, 'Please enter a valid number. Example: 50'
    if value < Decimal('0.1') or value > Decimal('5000'):
        return False, 0.0, 'Quantity must be between 0.1 KG and 5000 KG.'
    return True, float(value.quantize(Decimal('0.01'))), ''


def validate_price(text: str, crop: str, mandi_price: float) -> tuple[bool, float, str, bool]:
    value = _parse_decimal(text)
    if value is None:
        return False, 0.0, 'Please enter a valid price. Example: 20', False
    if value <= 0:
        return False, 0.0, f'Please enter a positive price for {crop}.', False
    if value > Decimal('100000'):
        return False, 0.0, 'Please enter a realistic price per KG.', False

    reference = Decimal(str(mandi_price or 0))
    needs_confirmation = False
    if reference > 0:
        needs_confirmation = value < (reference * Decimal('0.4')) or value > (reference * Decimal('2.0'))
    return True, float(value.quantize(Decimal('0.01'))), '', needs_confirmation


def validate_amount(
    text: str,
    min_amt: float,
    max_amt: float,
    balance: float | None = None,
    current_balance: float | None = None,
) -> tuple[bool, float, str]:
    value = _parse_decimal(text)
    if value is None:
        return False, 0.0, 'Please enter a valid amount.'

    minimum = Decimal(str(min_amt))
    maximum = Decimal(str(max_amt))
    available = current_balance if current_balance is not None else balance

    if value < minimum or value > maximum:
        return False, 0.0, f'Amount must be between ₹{minimum:.2f} and ₹{maximum:.2f}.'
    if available is not None and value > Decimal(str(available)):
        return False, 0.0, 'This amount is higher than your available balance.'
    return True, float(value.quantize(Decimal('0.01'))), ''


def validate_upi(text: str) -> bool:
    candidate = (text or '').strip()
    return bool(UPI_PATTERN.fullmatch(candidate))


def validate_menu_choice(text: str, max_opt: int) -> tuple[bool, int]:
    candidate = (text or '').strip()
    if not candidate.isdigit():
        return False, 0
    choice = int(candidate)
    return (1 <= choice <= max_opt), choice


def validate_name(text: str) -> tuple[bool, str]:
    normalized = ' '.join((text or '').strip().split())
    if len(normalized) < 3 or len(normalized) > 50:
        return False, 'Name must be between 3 and 50 characters.'

    for char in normalized:
        if char in {' ', '.', '-', '\''}:
            continue
        if not unicodedata.category(char).startswith('L'):
            return False, 'Name can contain only letters, spaces, dots, apostrophes, and hyphens.'
    return True, normalized
