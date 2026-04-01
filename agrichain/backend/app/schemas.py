from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar

import phonenumbers
from pydantic import BaseModel, ConfigDict, Field, field_validator


DataT = TypeVar('DataT')
ALLOWED_LANGUAGES = {'en', 'kn', 'hi', 'te'}
ALLOWED_PICKUP_TYPES = {'at_farm', 'nearest_mandi', 'farmer_delivers'}
ALLOWED_MARKET_TYPES = {'local', 'global', 'both'}
ALLOWED_LISTING_MARKET_TYPES = {'local', 'global'}
ALLOWED_USER_TYPES = {'farmer', 'buyer'}


class Envelope(BaseModel, Generic[DataT]):
    success: bool
    data: DataT | None
    error: str | None


class OTPRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=20)

    @field_validator('phone')
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        candidate = value.strip()
        try:
            parsed = phonenumbers.parse(candidate, 'IN')
            if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
                raise ValueError
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except Exception as exc:
            raise ValueError('Enter a valid phone number.') from exc


class OTPVerifyRequest(OTPRequest):
    otp: str = Field(min_length=6, max_length=6)

    @field_validator('otp')
    @classmethod
    def validate_otp(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.isdigit() or len(normalized) != 6:
            raise ValueError('Enter a valid 6-digit OTP.')
        return normalized


class RegisterRequest(OTPRequest):
    name: str = Field(min_length=3, max_length=50)
    village: str | None = Field(default=None, max_length=100)
    user_type: str = Field(min_length=5, max_length=20)
    language: str = Field(default='en', min_length=2, max_length=5)
    market_type: str = Field(default='local', min_length=5, max_length=20)

    @field_validator('name')
    @classmethod
    def normalize_name(cls, value: str) -> str:
        cleaned = ' '.join(value.strip().split())
        if len(cleaned) < 3:
            raise ValueError('Name must be at least 3 characters long.')
        return cleaned

    @field_validator('village')
    @classmethod
    def normalize_village(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = ' '.join(value.strip().split())
        if len(cleaned) < 2:
            raise ValueError('Village must be at least 2 characters long.')
        return cleaned

    @field_validator('user_type')
    @classmethod
    def validate_user_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_USER_TYPES:
            raise ValueError('Unsupported user type.')
        return normalized

    @field_validator('language')
    @classmethod
    def validate_language(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_LANGUAGES:
            raise ValueError('Unsupported language.')
        return normalized

    @field_validator('market_type')
    @classmethod
    def validate_market_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_LISTING_MARKET_TYPES:
            raise ValueError('Unsupported market type.')
        return normalized


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=50)
    village: str | None = Field(default=None, max_length=100)
    language: str | None = Field(default=None, max_length=5)

    @field_validator('name')
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        return ' '.join(value.strip().split()) if value is not None else None

    @field_validator('village')
    @classmethod
    def normalize_village(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = ' '.join(value.strip().split())
        if len(cleaned) < 2:
            raise ValueError('Village must be at least 2 characters long.')
        return cleaned

    @field_validator('language')
    @classmethod
    def validate_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in ALLOWED_LANGUAGES:
            raise ValueError('Unsupported language.')
        return normalized


class WalletAddRequest(BaseModel):
    amount: Decimal

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError('Amount must be greater than zero.')
        return value.quantize(Decimal('0.01'))


class WalletWithdrawRequest(WalletAddRequest):
    upi_id: str

    @field_validator('upi_id')
    @classmethod
    def normalize_upi(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) < 5:
            raise ValueError('Enter a valid UPI ID.')
        return normalized


class ListingCreateRequest(BaseModel):
    crop_name: str = Field(min_length=2, max_length=100)
    quantity_kg: Decimal = Field(gt=0)
    price_per_kg: Decimal = Field(gt=0)
    pickup_type: str = Field(min_length=3, max_length=30)
    market_type: str | None = Field(default=None, max_length=20)
    gi_tag: str | None = Field(default=None, max_length=100)
    organic_certified: bool = False

    @field_validator('crop_name')
    @classmethod
    def normalize_crop(cls, value: str) -> str:
        cleaned = ' '.join(value.strip().split()).lower()
        if len(cleaned) < 2:
            raise ValueError('Enter a valid crop name.')
        return cleaned

    @field_validator('quantity_kg', 'price_per_kg')
    @classmethod
    def quantize_decimal(cls, value: Decimal) -> Decimal:
        return value.quantize(Decimal('0.01'))

    @field_validator('pickup_type')
    @classmethod
    def validate_pickup_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_PICKUP_TYPES:
            raise ValueError('Unsupported pickup type.')
        return normalized

    @field_validator('market_type')
    @classmethod
    def validate_market_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in ALLOWED_LISTING_MARKET_TYPES:
            raise ValueError('Unsupported market type.')
        return normalized

    @field_validator('gi_tag')
    @classmethod
    def normalize_gi_tag(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = ' '.join(value.strip().split())
        return cleaned or None


class ListingUpdateRequest(BaseModel):
    quantity_kg: Decimal | None = Field(default=None, gt=0)
    price_per_kg: Decimal | None = Field(default=None, gt=0)
    pickup_type: str | None = Field(default=None, min_length=3, max_length=30)
    gi_tag: str | None = Field(default=None, max_length=100)
    organic_certified: bool | None = None

    @field_validator('quantity_kg', 'price_per_kg')
    @classmethod
    def quantize_optional_decimal(cls, value: Decimal | None) -> Decimal | None:
        return value.quantize(Decimal('0.01')) if value is not None else None

    @field_validator('pickup_type')
    @classmethod
    def validate_optional_pickup_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in ALLOWED_PICKUP_TYPES:
            raise ValueError('Unsupported pickup type.')
        return normalized

    @field_validator('gi_tag')
    @classmethod
    def normalize_optional_gi_tag(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = ' '.join(value.strip().split())
        return cleaned or None


class ListingPurchaseRequest(BaseModel):
    quantity_kg: Decimal = Field(gt=0)

    @field_validator('quantity_kg')
    @classmethod
    def quantize_quantity(cls, value: Decimal) -> Decimal:
        return value.quantize(Decimal('0.01'))



class OrderConfirmRequest(BaseModel):
    release_key: str | None = Field(default=None, min_length=6, max_length=20)

    @field_validator('release_key')
    @classmethod
    def normalize_release_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not normalized.isalnum():
            raise ValueError('Enter a valid release key.')
        return normalized

class UserProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    phone: str
    name: str
    village: str | None
    user_type: str
    language: str
    market_type: str
    reputation_score: Decimal
    created_at: datetime


class TokenUserOut(BaseModel):
    id: str
    name: str
    phone: str
    village: str | None
    user_type: str
    language: str
    market_type: str


class TokenOut(BaseModel):
    token: str
    user: TokenUserOut







