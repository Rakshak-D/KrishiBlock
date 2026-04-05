from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.config import get_settings


settings = get_settings()
SUPPORTED_LANGUAGES = ('en', 'kn', 'hi', 'te')
CROP_OPTIONS = [
    'tomato',
    'potato',
    'onion',
    'ginger',
    'carrot',
    'cabbage',
    'cauliflower',
    'brinjal',
    'beans',
    'peas',
]


@lru_cache(maxsize=16)
def _load_translation(language: str) -> dict[str, str]:
    path = settings.i18n_dir / f'{language}.json'
    if not path.exists():
        path = settings.i18n_dir / 'en.json'
    return json.loads(path.read_text(encoding='utf-8'))


def t(key: str, language: str, **kwargs: object) -> str:
    lang = language if language in SUPPORTED_LANGUAGES else 'en'
    translations = _load_translation(lang)
    fallback = _load_translation('en')
    template = translations.get(key) or fallback.get(key, key)
    return template.format(**kwargs) if kwargs else template


def crop_name(index: int) -> str:
    return CROP_OPTIONS[index]


def crop_menu(language: str) -> str:
    lines = [t('crop_menu_header', language)]
    for idx, crop in enumerate(CROP_OPTIONS, start=1):
        lines.append(f'{idx}. {t(f"crop_{crop}", language)}')
    return '\n'.join(lines)
