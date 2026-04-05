from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.nodes import main_menu_key
from app.graph.state import ConversationState
from app.models.user import MarketType, User, UserType
from app.services.wallet_service import ensure_wallet
from app.utils.id_generator import generate_user_id
from app.utils.i18n import t
from app.utils.validators import validate_menu_choice, validate_name


LANGUAGE_MAP = {1: 'en', 2: 'kn', 3: 'hi', 4: 'te'}
USER_TYPE_MAP = {1: UserType.FARMER, 2: UserType.BUYER}
MARKET_TYPE_MAP = {1: MarketType.LOCAL, 2: MarketType.GLOBAL, 3: MarketType.BOTH}


async def handle_registration(state: ConversationState, message: str, db: AsyncSession) -> ConversationState:
    step = state['flow_step']
    if step == 0:
        valid, choice = validate_menu_choice(message, 4)
        if not valid:
            state['response'] = t('choose_language', state['language'])
            return state
        state['language'] = LANGUAGE_MAP[choice]
        state['flow_step'] = 1
        state['response'] = t('choose_role', state['language'])
        return state

    if step == 1:
        valid, choice = validate_menu_choice(message, 2)
        if not valid:
            state['response'] = t('choose_role', state['language'])
            return state
        state['user_type'] = USER_TYPE_MAP[choice].value
        state['flow_step'] = 2
        state['response'] = t('ask_name', state['language'])
        return state

    if step == 2:
        valid, name_or_error = validate_name(message)
        if not valid:
            state['response'] = name_or_error
            return state
        state['temp']['name'] = name_or_error
        state['flow_step'] = 3
        state['response'] = t('ask_village', state['language'])
        return state

    if step == 3:
        state['temp']['village'] = ' '.join(message.strip().split())[:100]
        state['flow_step'] = 4
        state['response'] = t('ask_market_type', state['language'])
        return state

    if step == 4:
        valid, choice = validate_menu_choice(message, 3)
        if not valid:
            state['response'] = t('ask_market_type', state['language'])
            return state
        state['temp']['market_type'] = MARKET_TYPE_MAP[choice].value
        state['flow_step'] = 5
        state['response'] = t(
            'registration_confirm',
            state['language'],
            name=state['temp']['name'],
            village=state['temp']['village'],
            role=t(f'user_type_{state["user_type"]}', state['language']),
            market=t(f'market_{state["temp"]["market_type"]}', state['language']),
        )
        return state

    if step == 5:
        if message.strip().upper() != 'YES':
            state['flow_step'] = 0
            state['temp'] = {}
            state['response'] = t('registration_restart', state['language'])
            return state

        result = await db.execute(select(User).where(User.phone == state['phone']))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                id=await generate_user_id(db),
                phone=state['phone'],
                name=state['temp']['name'],
                village=state['temp']['village'],
                user_type=UserType(state['user_type']),
                language=state['language'],
                market_type=MarketType(state['temp']['market_type']),
            )
            db.add(user)
            await db.flush()
        else:
            user.name = state['temp']['name']
            user.village = state['temp']['village']
            user.user_type = UserType(state['user_type'])
            user.language = state['language']
            user.market_type = MarketType(state['temp']['market_type'])

        wallet = await ensure_wallet(db, user, welcome_bonus=True)
        state['user_id'] = user.id
        state['is_registered'] = True
        state['current_flow'] = None
        state['flow_step'] = 0
        state['temp'] = {}
        state['response'] = '\n\n'.join(
            [
                t('registration_complete', state['language'], agr_id=user.id, balance=f'{wallet.balance:.2f}', name=user.name),
                t(main_menu_key(user.user_type.value), state['language'], name=user.name),
            ]
        )
        return state

    state['response'] = t('choose_language', state['language'])
    return state
