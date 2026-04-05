from __future__ import annotations

from typing import Literal, TypedDict

from app.utils.i18n import t


LanguageCode = Literal['en', 'kn', 'hi', 'te']
UserRole = Literal['farmer', 'buyer']
FlowName = Literal['registration', 'sell', 'buy', 'wallet', 'history', 'idle']


class ConversationState(TypedDict):
    phone: str
    user_id: str | None
    language: LanguageCode
    user_type: UserRole | None
    is_registered: bool
    current_flow: FlowName | None
    flow_step: int
    temp: dict[str, object]
    last_message: str
    response: str
    media_url: str | None
    error: str | None


def build_default_state(phone: str) -> ConversationState:
    return {
        'phone': phone,
        'user_id': None,
        'language': 'en',
        'user_type': None,
        'is_registered': False,
        'current_flow': None,
        'flow_step': 0,
        'temp': {},
        'last_message': '',
        'response': t('choose_language', 'en'),
        'media_url': None,
        'error': None,
    }
