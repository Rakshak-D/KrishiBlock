from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import get_settings


settings = get_settings()
ALGORITHM = 'HS256'
TokenExtra = str | int | float | bool


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def create_access_token(subject: str, extra: dict[str, TokenExtra] | None = None) -> str:
    payload: dict[str, object] = {
        'sub': subject,
        'exp': datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, object]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError('Invalid or expired token.') from exc


def hash_otp(otp: str) -> str:
    secret = f'{settings.SECRET_KEY}:{otp}'.encode('utf-8')
    return hashlib.sha256(secret).hexdigest()


def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    expected = hash_otp(plain_otp)
    return hmac.compare_digest(expected, hashed_otp)
