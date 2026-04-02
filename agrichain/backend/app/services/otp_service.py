from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.services.session import clear_otp, load_otp, store_otp
from app.services.whatsapp import whatsapp_service
from app.utils.id_generator import generate_otp_code
from app.utils.security import hash_otp, verify_otp


settings = get_settings()


async def request_otp(phone: str) -> dict[str, object]:
    otp = generate_otp_code()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_EXPIRY_SECONDS)
    await store_otp(
        phone,
        {
            'otp_hash': hash_otp(otp),
            'attempts': 0,
            'expires_at': expires_at.isoformat(),
            'locked_until': None,
        },
        ttl=settings.OTP_EXPIRY_SECONDS,
    )
    delivered = await whatsapp_service.send_message(
        to=phone,
        body=f'Your KrishiBlock login OTP is {otp}. It will expire in 10 minutes.',
    )
    return {'delivered': delivered, 'otp': otp if settings.is_development else None}


async def verify_otp_code(phone: str, otp: str) -> tuple[bool, str]:
    payload = await load_otp(phone)
    if payload is None:
        return False, 'OTP expired or not requested yet.'

    now = datetime.now(timezone.utc)
    locked_until = payload.get('locked_until')
    if locked_until:
        lock_time = datetime.fromisoformat(locked_until)
        if lock_time > now:
            return False, 'Too many failed attempts. Please wait 15 minutes and try again.'

    expires_at = datetime.fromisoformat(payload['expires_at'])
    if expires_at <= now:
        await clear_otp(phone)
        return False, 'OTP expired. Please request a fresh code.'

    if not verify_otp(otp, payload['otp_hash']):
        attempts = int(payload['attempts']) + 1
        payload['attempts'] = attempts
        ttl = max(1, int((expires_at - now).total_seconds()))
        if attempts >= settings.OTP_MAX_ATTEMPTS:
            payload['locked_until'] = (now + timedelta(seconds=settings.OTP_LOCKOUT_SECONDS)).isoformat()
            ttl = settings.OTP_LOCKOUT_SECONDS
        await store_otp(phone, payload, ttl=ttl)
        return False, 'Invalid OTP. Please try again.'

    await clear_otp(phone)
    return True, 'OTP verified successfully.'
