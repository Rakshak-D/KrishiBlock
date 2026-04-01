from __future__ import annotations

from contextvars import ContextVar

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.graph.flows.buy import handle_buy_flow
from app.graph.flows.history import build_history_message
from app.graph.flows.registration import handle_registration
from app.graph.flows.sell import handle_sell_flow
from app.graph.flows.wallet import handle_wallet_flow
from app.graph.nodes import main_menu_key
from app.graph.state import ConversationState, build_default_state
from app.models.listing import Listing
from app.models.order import Order
from app.models.user import User
from app.services.wallet_service import confirm_order_delivery
from app.utils.i18n import crop_menu, t
from app.utils.validators import validate_menu_choice


_db_context: ContextVar[AsyncSession] = ContextVar('conversation_db')
_message_context: ContextVar[str] = ContextVar('conversation_message')
_user_context: ContextVar[User | None] = ContextVar('conversation_user')


class ConversationEngine:
    def __init__(self) -> None:
        graph = StateGraph(ConversationState)
        graph.add_node('registration', self._registration_node)
        graph.add_node('sell', self._sell_node)
        graph.add_node('buy', self._buy_node)
        graph.add_node('wallet', self._wallet_node)
        graph.add_node('confirm', self._confirm_node)
        graph.add_node('idle', self._idle_node)
        graph.add_conditional_edges(
            START,
            self._route,
            {
                'registration': 'registration',
                'sell': 'sell',
                'buy': 'buy',
                'wallet': 'wallet',
                'confirm': 'confirm',
                'idle': 'idle',
            },
        )
        for node_name in ['registration', 'sell', 'buy', 'wallet', 'confirm', 'idle']:
            graph.add_edge(node_name, END)
        self.graph = graph.compile()

    def default_state(self, phone: str) -> ConversationState:
        return build_default_state(phone)

    async def process(self, phone: str, message: str, session: ConversationState | None, db: AsyncSession) -> dict[str, object]:
        state = dict(session or self.default_state(phone))
        state.setdefault('temp', {})
        state['phone'] = phone
        state['last_message'] = message
        state['media_url'] = None
        state['error'] = None

        result = await db.execute(select(User).where(User.phone == phone).options(selectinload(User.wallet)))
        user = result.scalar_one_or_none()
        if user is not None:
            state['user_id'] = user.id
            state['language'] = user.language
            state['user_type'] = user.user_type.value
            state['is_registered'] = True

        db_token = _db_context.set(db)
        message_token = _message_context.set(message)
        user_token = _user_context.set(user)
        try:
            try:
                updated_state = await self.graph.ainvoke(state)
                await db.commit()
            except ValueError as exc:
                await db.rollback()
                updated_state = state
                updated_state['response'] = str(exc)
            except Exception:
                await db.rollback()
                updated_state = state
                updated_state['response'] = t('error_generic', state['language'])
        finally:
            _db_context.reset(db_token)
            _message_context.reset(message_token)
            _user_context.reset(user_token)

        return {'state': updated_state, 'response': updated_state['response'], 'media_url': updated_state.get('media_url')}

    def _route(self, state: ConversationState) -> str:
        message = _message_context.get('').strip()
        if message.upper().startswith('CONFIRM ') and state['is_registered']:
            return 'confirm'
        if not state['is_registered']:
            return 'registration'
        if state['current_flow'] == 'sell':
            return 'sell'
        if state['current_flow'] == 'buy':
            return 'buy'
        if state['current_flow'] == 'wallet':
            return 'wallet'
        return 'idle'

    async def _registration_node(self, state: ConversationState) -> ConversationState:
        return await handle_registration(state, _message_context.get(''), _db_context.get())

    async def _sell_node(self, state: ConversationState) -> ConversationState:
        user = _user_context.get()
        if user is None:
            state['response'] = t('auth_required', state['language'])
            return state
        return await handle_sell_flow(state, _message_context.get(''), _db_context.get(), user)

    async def _buy_node(self, state: ConversationState) -> ConversationState:
        user = _user_context.get()
        if user is None:
            state['response'] = t('auth_required', state['language'])
            return state
        return await handle_buy_flow(state, _message_context.get(''), _db_context.get(), user)

    async def _wallet_node(self, state: ConversationState) -> ConversationState:
        user = _user_context.get()
        if user is None:
            state['response'] = t('auth_required', state['language'])
            return state
        return await handle_wallet_flow(state, _message_context.get(''), _db_context.get(), user)

    async def _confirm_node(self, state: ConversationState) -> ConversationState:
        return await self._handle_confirm_command(state, _message_context.get(''), _db_context.get(), _user_context.get())

    async def _idle_node(self, state: ConversationState) -> ConversationState:
        user = _user_context.get()
        if user is None:
            state['response'] = t('choose_language', state['language'])
            return state
        return await self._handle_idle_message(state, _message_context.get(''), _db_context.get(), user)

    async def _handle_confirm_command(self, state: ConversationState, message: str, db: AsyncSession, user: User | None) -> ConversationState:
        if user is None:
            state['response'] = t('auth_required', state['language'])
            return state
        order_id = message.split(maxsplit=1)[1].strip()
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.listing).selectinload(Listing.farmer), selectinload(Order.buyer))
        )
        order = result.scalar_one_or_none()
        if order is None:
            state['response'] = t('order_not_found', state['language'], order_id=order_id)
            return state
        await confirm_order_delivery(db, order=order, buyer=user)
        state['current_flow'] = None
        state['flow_step'] = 0
        state['temp'] = {}
        state['response'] = '\n'.join(
            [
                t('delivery_confirmed_buyer', state['language'], order_id=order.id),
                t('delivery_confirmed_farmer', state['language'], order_id=order.id, amount=f'{order.total_amount - order.platform_fee:.2f}'),
            ]
        )
        return state

    async def _handle_idle_message(self, state: ConversationState, message: str, db: AsyncSession, user: User) -> ConversationState:
        text = message.strip().upper()
        if text in {'MENU', 'HI', 'HELLO', 'START'}:
            state['response'] = t(main_menu_key(state['user_type'] or user.user_type.value), state['language'], name=user.name)
            return state

        if state['user_type'] == 'farmer':
            valid, choice = validate_menu_choice(message, 5)
            if not valid:
                state['response'] = t(main_menu_key(user.user_type.value), state['language'], name=user.name)
                return state
            if choice == 1:
                state['current_flow'] = 'sell'
                state['flow_step'] = 0
                state['temp'] = {}
                state['response'] = crop_menu(state['language'])
                return state
            if choice == 2:
                state['response'] = await self._my_listings(user, db, state['language'])
                return state
            if choice == 3:
                state['current_flow'] = 'wallet'
                state['flow_step'] = 0
                state['temp'] = {}
                state['response'] = t('wallet_menu', state['language'])
                return state
            if choice == 4:
                state['response'] = await build_history_message(user, db, state['language'])
                return state
            state['response'] = await self._my_orders(user, db, state['language'])
            return state

        valid, choice = validate_menu_choice(message, 4)
        if not valid:
            state['response'] = t(main_menu_key(user.user_type.value), state['language'], name=user.name)
            return state
        if choice == 1:
            state['current_flow'] = 'buy'
            state['flow_step'] = 0
            state['temp'] = {}
            state['response'] = crop_menu(state['language'])
            return state
        if choice == 2:
            state['response'] = await self._my_orders(user, db, state['language'])
            return state
        if choice == 3:
            state['current_flow'] = 'wallet'
            state['flow_step'] = 0
            state['temp'] = {}
            state['response'] = t('wallet_menu', state['language'])
            return state
        state['response'] = await build_history_message(user, db, state['language'])
        return state

    async def _my_listings(self, user: User, db: AsyncSession, language: str) -> str:
        result = await db.execute(select(Listing).where(Listing.farmer_id == user.id).order_by(Listing.created_at.desc()).limit(5))
        listings = result.scalars().all()
        if not listings:
            return t('my_listings_empty', language)
        lines = [t('my_listings_header', language)]
        for listing in listings:
            lines.append(f'{listing.id}: {t(f"crop_{listing.crop_name}", language)} {listing.quantity_remaining:.2f}kg @ {listing.currency} {listing.price_per_kg:.2f} [{listing.status.value}]')
        return '\n'.join(lines)

    async def _my_orders(self, user: User, db: AsyncSession, language: str) -> str:
        result = await db.execute(select(Order).where(Order.buyer_id == user.id).options(selectinload(Order.listing)).order_by(Order.created_at.desc()).limit(5))
        orders = result.scalars().all()
        if not orders:
            return t('my_orders_empty', language)
        lines = [t('my_orders_header', language)]
        for order in orders:
            lines.append(f'{order.id}: {t(f"crop_{order.listing.crop_name}", language)} {order.quantity_kg:.2f}kg [{order.status.value}]')
        return '\n'.join(lines)


conversation_engine = ConversationEngine()
