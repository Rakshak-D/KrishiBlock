from __future__ import annotations

from decimal import Decimal

import httpx

from app.config import get_settings
from app.services.session import _get_json, _set_json


settings = get_settings()
FALLBACK_PRICES = {
    'tomato': 16.0,
    'potato': 14.0,
    'onion': 20.0,
    'ginger': 55.0,
    'carrot': 22.0,
    'cabbage': 11.0,
    'cauliflower': 18.0,
    'brinjal': 15.0,
    'beans': 32.0,
    'peas': 42.0,
    'rice': 28.0,
    'wheat': 22.0,
}
CACHE_TTL_SECONDS = 21600


async def get_mandi_price(crop: str, state: str = 'Karnataka') -> float:
    normalized_crop = crop.strip().lower()
    cache_key = f'mandi:{normalized_crop}:{state.lower()}'
    cached = await _get_json(cache_key)
    if isinstance(cached, dict) and 'price' in cached:
        return float(cached['price'])

    params = {
        'format': 'json',
        'limit': 1,
        'filters[commodity]': normalized_crop.title(),
        'filters[state]': state,
    }
    if settings.AGMARKNET_API_KEY:
        params['api-key'] = settings.AGMARKNET_API_KEY

    price = FALLBACK_PRICES.get(normalized_crop, 20.0)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(settings.AGMARKNET_API_URL, params=params)
            response.raise_for_status()
            payload = response.json()
            records = payload.get('records', []) if isinstance(payload, dict) else []
            if records:
                raw_price = records[0].get('modal_price') or records[0].get('modal price')
                parsed = Decimal(str(raw_price or 0))
                if parsed > 0:
                    price = float(parsed)
    except Exception:
        price = FALLBACK_PRICES.get(normalized_crop, 20.0)

    await _set_json(cache_key, {'price': price}, CACHE_TTL_SECONDS)
    return float(price)


async def refresh_mandi_cache() -> None:
    for crop in FALLBACK_PRICES:
        await get_mandi_price(crop, settings.DEFAULT_MANDI_STATE)
