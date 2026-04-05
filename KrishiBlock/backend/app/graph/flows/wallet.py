from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.graph.state import ConversationState
from app.models.transaction import Transaction
from app.models.user import User
from app.services.notification import send_notification
from app.services.wallet_service import create_withdrawal, credit_wallet, ensure_wallet
from app.utils.i18n import t
from app.utils.validators import validate_amount, validate_menu_choice, validate_upi


settings = get_settings()


async def handle_wallet_flow(state: ConversationState, message: str, db: AsyncSession, user: User) -> ConversationState:
    wallet = await ensure_wallet(db, user)

    if state['flow_step'] == 0:
        valid, choice = validate_menu_choice(message, 4)
        if not valid:
            state['response'] = t('wallet_menu', state['language'])
            return state
        if choice == 1:
            state['current_flow'] = None
            state['flow_step'] = 0
            state['response'] = t('wallet_balance', state['language'], balance=f'{wallet.balance:.2f}', locked=f'{wallet.locked_balance:.2f}')
            return state
        if choice == 2:
            state['temp'] = {'mode': 'add'}
            state['flow_step'] = 1
            state['response'] = t('wallet_add_ask_amount', state['language'])
            return state
        if choice == 3:
            state['temp'] = {'mode': 'withdraw'}
            state['flow_step'] = 1
            state['response'] = t('wallet_withdraw_ask_amount', state['language'])
            return state

        result = await db.execute(select(Transaction).where(Transaction.user_id == user.id).order_by(Transaction.created_at.desc(), Transaction.id.desc()).limit(5))
        transactions = result.scalars().all()
        if not transactions:
            state['current_flow'] = None
            state['response'] = t('wallet_no_transactions', state['language'])
            return state
        rows = '\n'.join(
            t('transaction_row', state['language'], id=tx.id, type=tx.type.value, amount=f'{tx.amount:.2f}', ref=tx.reference_id or '-')
            for tx in transactions
        )
        state['current_flow'] = None
        state['response'] = t('mini_statement', state['language'], rows=rows)
        return state

    if state['flow_step'] == 1 and state['temp'].get('mode') == 'add':
        valid, amount, error = validate_amount(message, float(settings.MIN_ADD_AMOUNT), float(settings.MAX_WALLET_BALANCE))
        if not valid:
            state['response'] = error
            return state
        if wallet.balance + Decimal(str(amount)) > settings.MAX_WALLET_BALANCE:
            state['response'] = t('wallet_add_limit', state['language'])
            return state
        state['temp']['amount'] = f'{amount:.2f}'
        state['flow_step'] = 2
        state['response'] = t('wallet_add_confirm', state['language'], amount=f'{amount:.2f}')
        return state

    if state['flow_step'] == 2 and state['temp'].get('mode') == 'add':
        if message.strip().upper() != 'YES':
            state['current_flow'] = None
            state['flow_step'] = 0
            state['temp'] = {}
            state['response'] = t('action_cancelled', state['language'])
            return state
        amount = Decimal(str(state['temp']['amount']))
        wallet = await credit_wallet(db, user=user, amount=amount, description='Simulated wallet top-up completed.')
        await send_notification(user.phone, 'wallet_credited', {'amount': f'{amount:.2f}', 'balance': f'{wallet.balance:.2f}'}, user.language)

        if state['temp'].get('resume_flow') == 'buy':
            resume_state = state['temp'].get('resume_state')
            if isinstance(resume_state, dict):
                state['current_flow'] = 'buy'
                state['flow_step'] = 3
                state['temp'] = dict(resume_state)
                state['response'] = t(
                    'buy_summary',
                    state['language'],
                    crop=t(f'crop_{state["temp"]["crop"]}', state['language']),
                    qty=str(state['temp']['quantity_kg']),
                    farmer=str(state['temp']['farmer_name']),
                    price=str(state['temp']['unit_price']),
                    total=str(state['temp']['total_amount']),
                    fee=str(state['temp']['platform_fee']),
                    currency_symbol='$' if state['temp'].get('currency') == 'USD' else '₹',
                )
                return state

        state['current_flow'] = None
        state['flow_step'] = 0
        state['temp'] = {}
        state['response'] = t('wallet_add_done', state['language'], amount=f'{amount:.2f}', balance=f'{wallet.balance:.2f}')
        return state

    if state['flow_step'] == 1 and state['temp'].get('mode') == 'withdraw':
        valid, amount, error = validate_amount(message, float(settings.MIN_ADD_AMOUNT), float(wallet.balance), current_balance=float(wallet.balance))
        if not valid:
            state['response'] = error
            return state
        state['temp']['amount'] = f'{amount:.2f}'
        state['flow_step'] = 2
        state['response'] = t('wallet_withdraw_ask_upi', state['language'])
        return state

    if state['flow_step'] == 2 and state['temp'].get('mode') == 'withdraw':
        if not validate_upi(message):
            state['response'] = t('wallet_invalid_upi', state['language'])
            return state
        amount = Decimal(str(state['temp']['amount']))
        withdrawal = await create_withdrawal(db, user=user, amount=amount, upi_id=message.strip())
        state['current_flow'] = None
        state['flow_step'] = 0
        state['temp'] = {}
        state['response'] = t('wallet_withdraw_processing', state['language'], amount=f'{amount:.2f}', upi_id=withdrawal.upi_id)
        return state

    state['response'] = t('wallet_menu', state['language'])
    return state
