from __future__ import annotations

from app.utils.i18n import t


def main_menu_key(user_type: str) -> str:
    return 'main_menu_farmer' if user_type == 'farmer' else 'main_menu_buyer'


def start_flow(state: dict, flow: str) -> dict:
    state['current_flow'] = flow
    state['flow_step'] = 0
    state['temp'] = {}
    state['media_url'] = None
    state['error'] = None
    return state


def reset_to_menu(state: dict, name: str) -> dict:
    state['current_flow'] = None
    state['flow_step'] = 0
    state['temp'] = {}
    state['response'] = t(main_menu_key(state['user_type'] or 'buyer'), state['language'], name=name)
    state['media_url'] = None
    return state
