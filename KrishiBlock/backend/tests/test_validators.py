from app.utils.validators import (
    validate_amount,
    validate_menu_choice,
    validate_name,
    validate_price,
    validate_quantity,
    validate_upi,
)


def test_validate_quantity_accepts_valid_number():
    ok, value, error = validate_quantity('50.5')
    assert ok is True
    assert value == 50.5
    assert error == ''


def test_validate_quantity_rejects_non_numeric():
    ok, value, error = validate_quantity('abc')
    assert ok is False
    assert value == 0.0
    assert 'valid number' in error.lower()


def test_validate_price_warns_when_far_from_mandi_rate():
    ok, price, error, warn = validate_price('100', 'tomato', 20)
    assert ok is True
    assert price == 100.0
    assert error == ''
    assert warn is True


def test_validate_name_normalizes_spacing():
    ok, cleaned = validate_name('  Ramesh   Kumar  ')
    assert ok is True
    assert cleaned == 'Ramesh Kumar'


def test_validate_upi_matches_expected_patterns():
    assert validate_upi('ramesh@upi') is True
    assert validate_upi('9876543210@upi') is True
    assert validate_upi('bad-upi') is False


def test_validate_menu_choice_bounds():
    assert validate_menu_choice('2', 4) == (True, 2)
    assert validate_menu_choice('9', 4) == (False, 9)


def test_validate_amount_respects_balance():
    ok, amount, error = validate_amount('500', 10, 1000, current_balance=100)
    assert ok is False
    assert amount == 0.0
    assert 'available balance' in error.lower()
