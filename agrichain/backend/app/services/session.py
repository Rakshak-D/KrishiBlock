from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import TypedDict

from redis.asyncio import Redis

from app.config import get_settings
from app.graph.state import ConversationState, build_default_state


class OTPState(TypedDict):
    otp_hash: str
    attempts: int
    expires_at: str
    locked_until: str | None


settings = get_settings()
redis_client: Redis | None = None
memory_store: dict[str, tuple[object, datetime]] = {}


async def _drop_redis_client() -> None:
    global redis_client
    client = redis_client
    redis_client = None
    if client is not None:
        try:
            await client.aclose()
        except Exception:
            pass


async def get_redis() -> Redis | None:
    global redis_client
    if redis_client is not None:
        return redis_client
    try:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        return redis_client
    except Exception:
        await _drop_redis_client()
        return None


async def _set_json(key: str, value: object, ttl: int) -> None:
    client = await get_redis()
    if client is not None:
        try:
            await client.set(key, json.dumps(value, default=str), ex=ttl)
            return
        except Exception:
            await _drop_redis_client()
    memory_store[key] = (value, datetime.now(timezone.utc) + timedelta(seconds=ttl))


async def _get_json(key: str) -> object | None:
    client = await get_redis()
    if client is not None:
        try:
            value = await client.get(key)
            return json.loads(value) if value else None
        except Exception:
            await _drop_redis_client()

    payload = memory_store.get(key)
    if payload is None:
        return None
    value, expiry = payload
    if expiry <= datetime.now(timezone.utc):
        memory_store.pop(key, None)
        return None
    return value


async def _delete(key: str) -> None:
    client = await get_redis()
    if client is not None:
        try:
            await client.delete(key)
            return
        except Exception:
            await _drop_redis_client()
    memory_store.pop(key, None)


async def load_session(phone: str) -> ConversationState:
    payload = await _get_json(f'session:{phone}')
    if not isinstance(payload, dict):
        return build_default_state(phone)
    state = build_default_state(phone)
    state.update(payload)
    state['phone'] = phone
    return state


async def save_session(phone: str, state: ConversationState) -> None:
    await _set_json(f'session:{phone}', state, settings.SESSION_TTL_SECONDS)


async def clear_session(phone: str) -> None:
    await _delete(f'session:{phone}')


async def increment_rate_limit(phone: str, bucket: str, ttl: int) -> int:
    key = f'rate:{bucket}:{phone}'
    client = await get_redis()
    if client is not None:
        try:
            count = await client.incr(key)
            if count == 1:
                await client.expire(key, ttl)
            return int(count)
        except Exception:
            await _drop_redis_client()

    payload = await _get_json(key)
    current = int(payload['count']) if isinstance(payload, dict) and 'count' in payload else 0
    current += 1
    await _set_json(key, {'count': current}, ttl)
    return current


async def store_otp(phone: str, payload: OTPState, ttl: int | None = None) -> None:
    await _set_json(f'otp:{phone}', payload, ttl or settings.OTP_EXPIRY_SECONDS)


async def load_otp(phone: str) -> OTPState | None:
    payload = await _get_json(f'otp:{phone}')
    if not isinstance(payload, dict):
        return None
    return OTPState(
        otp_hash=str(payload.get('otp_hash', '')),
        attempts=int(payload.get('attempts', 0)),
        expires_at=str(payload.get('expires_at', '')),
        locked_until=str(payload['locked_until']) if payload.get('locked_until') else None,
    )


async def clear_otp(phone: str) -> None:
    await _delete(f'otp:{phone}')
