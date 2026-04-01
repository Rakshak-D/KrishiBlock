from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.graph.flows.buy import handle_buy_flow
from app.graph.flows.registration import handle_registration
from app.graph.flows.wallet import handle_wallet_flow
from app.models.listing import Listing, ListingMarketType, PickupType
from app.models.order import Order, OrderStatus
from app.models.transaction import Transaction
from app.models.user import MarketType, User, UserType
from app.models.wallet import Wallet
from app.services.conversation import conversation_engine
from app.services.qr_service import build_dpp
from app.services.wallet_service import confirm_order_delivery, credit_wallet, ensure_wallet, mark_order_in_transit, place_order
from app.utils.blockchain_sim import verify_transaction_chain
from app.utils.id_generator import generate_id


@pytest.mark.asyncio
async def test_registration_flow_creates_user_wallet_and_market_type(db_session):
    state = conversation_engine.default_state('+919999000001')

    for message in ['1', '1', 'Ramesh', 'Holenarasipur', '3', 'YES']:
        state = await handle_registration(state, message, db_session)

    await db_session.commit()
    user = (await db_session.execute(select(User).where(User.phone == '+919999000001'))).scalar_one()
    wallet = (await db_session.execute(select(Wallet).where(Wallet.user_id == user.id))).scalar_one()

    assert user.name == 'Ramesh'
    assert user.user_type == UserType.FARMER
    assert user.market_type == MarketType.BOTH
    assert wallet is not None
    assert float(wallet.balance) == 100.0


@pytest.mark.asyncio
async def test_order_confirmation_releases_escrow_logs_fee_and_keeps_chain_valid(db_session):
    farmer = User(
        id=generate_id('AGR'),
        phone='+919999000002',
        name='Farmer One',
        village='Village',
        user_type=UserType.FARMER,
        market_type=MarketType.BOTH,
        language='en',
    )
    buyer = User(
        id=generate_id('AGR'),
        phone='+919999000003',
        name='Buyer One',
        village='Town',
        user_type=UserType.BUYER,
        market_type=MarketType.LOCAL,
        language='en',
    )
    db_session.add_all([farmer, buyer])
    await db_session.flush()

    await ensure_wallet(db_session, farmer, welcome_bonus=True)
    await ensure_wallet(db_session, buyer)
    await credit_wallet(db_session, user=buyer, amount=Decimal('1000'), description='Seed wallet for test.')

    listing = Listing(
        id=generate_id('LST'),
        farmer_id=farmer.id,
        crop_name='tomato',
        quantity_kg=Decimal('50'),
        quantity_remaining=Decimal('50'),
        price_per_kg=Decimal('20'),
        currency='INR',
        market_type=ListingMarketType.GLOBAL,
        pickup_type=PickupType.AT_FARM,
        gi_tag='Mysore Silk Tomato',
        organic_certified=True,
        blockchain_hash='demo-hash',
    )
    db_session.add(listing)
    await db_session.flush()
    order = await place_order(db_session, buyer=buyer, listing=listing, quantity_kg=Decimal('10'))
    await db_session.flush()

    order = (await db_session.execute(select(Order).where(Order.id == order.id))).scalar_one()
    order.listing = listing
    order.listing.farmer = farmer

    await confirm_order_delivery(db_session, order=order, buyer=buyer)
    await db_session.commit()

    farmer_wallet = (await db_session.execute(select(Wallet).where(Wallet.user_id == farmer.id))).scalar_one()
    buyer_wallet = (await db_session.execute(select(Wallet).where(Wallet.user_id == buyer.id))).scalar_one()
    transactions = (await db_session.execute(select(Transaction).order_by(Transaction.created_at.asc(), Transaction.id.asc()))).scalars().all()

    assert float(farmer_wallet.balance) > 100.0
    assert float(buyer_wallet.locked_balance) == 0.0
    assert any(tx.type.value == 'fee' for tx in transactions)
    assert verify_transaction_chain(transactions) is True

    dpp = build_dpp(listing, farmer, [order])
    assert dpp['product']['gi_tag'] == 'Mysore Silk Tomato'
    assert dpp['product']['organic'] is True


@pytest.mark.asyncio
async def test_wallet_flow_adds_money_and_creates_credit_transaction(db_session, monkeypatch):
    async def fast_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr('app.graph.flows.wallet.asyncio.sleep', fast_sleep)

    user = User(
        id=generate_id('AGR'),
        phone='+919999000004',
        name='Lakshmi',
        village='Mandya',
        user_type=UserType.FARMER,
        market_type=MarketType.LOCAL,
        language='en',
    )
    db_session.add(user)
    await db_session.flush()
    await ensure_wallet(db_session, user, welcome_bonus=True)

    state = conversation_engine.default_state(user.phone)
    state.update({'is_registered': True, 'user_id': user.id, 'user_type': 'farmer', 'current_flow': 'wallet', 'language': 'en'})

    state = await handle_wallet_flow(state, '2', db_session, user)
    state = await handle_wallet_flow(state, '50', db_session, user)
    state = await handle_wallet_flow(state, 'YES', db_session, user)
    await db_session.commit()

    wallet = (await db_session.execute(select(Wallet).where(Wallet.user_id == user.id))).scalar_one()
    transactions = (await db_session.execute(select(Transaction).where(Transaction.user_id == user.id))).scalars().all()

    assert float(wallet.balance) == 150.0
    assert any(tx.type.value == 'credit' for tx in transactions)
    assert '₹50.00 added successfully' in state['response']


@pytest.mark.asyncio
async def test_buy_flow_can_resume_after_wallet_top_up(db_session):
    farmer = User(
        id=generate_id('AGR'),
        phone='+919999000005',
        name='Farmer Demo',
        village='Village',
        user_type=UserType.FARMER,
        market_type=MarketType.LOCAL,
        language='en',
    )
    buyer = User(
        id=generate_id('AGR'),
        phone='+919999000006',
        name='Buyer Demo',
        village='Town',
        user_type=UserType.BUYER,
        market_type=MarketType.LOCAL,
        language='en',
    )
    db_session.add_all([farmer, buyer])
    await db_session.flush()

    await ensure_wallet(db_session, farmer, welcome_bonus=True)
    await ensure_wallet(db_session, buyer)

    listing = Listing(
        id=generate_id('LST'),
        farmer_id=farmer.id,
        crop_name='tomato',
        quantity_kg=Decimal('25'),
        quantity_remaining=Decimal('25'),
        price_per_kg=Decimal('20'),
        currency='INR',
        market_type=ListingMarketType.LOCAL,
        pickup_type=PickupType.AT_FARM,
        blockchain_hash='demo-hash-2',
    )
    db_session.add(listing)
    await db_session.flush()

    state = conversation_engine.default_state(buyer.phone)
    state.update({'is_registered': True, 'user_id': buyer.id, 'user_type': 'buyer', 'current_flow': 'buy', 'language': 'en'})

    state = await handle_buy_flow(state, '1', db_session, buyer)
    state = await handle_buy_flow(state, '1', db_session, buyer)
    state = await handle_buy_flow(state, '10', db_session, buyer)

    assert state['flow_step'] == 21
    assert 'Insufficient balance' in state['response']

    state = await handle_buy_flow(state, '1', db_session, buyer)
    assert state['current_flow'] == 'wallet'
    assert state['temp']['resume_flow'] == 'buy'

    state = await handle_wallet_flow(state, '200', db_session, buyer)
    state = await handle_wallet_flow(state, 'YES', db_session, buyer)

    assert state['current_flow'] == 'buy'
    assert state['flow_step'] == 3
    assert 'Order summary' in state['response']


@pytest.mark.asyncio
async def test_farmer_can_mark_order_in_transit_before_delivery_confirmation(db_session):
    farmer = User(
        id=generate_id('AGR'),
        phone='+919999000007',
        name='Farmer Transit',
        village='Village',
        user_type=UserType.FARMER,
        market_type=MarketType.LOCAL,
        language='en',
    )
    buyer = User(
        id=generate_id('AGR'),
        phone='+919999000008',
        name='Buyer Transit',
        village='Town',
        user_type=UserType.BUYER,
        market_type=MarketType.LOCAL,
        language='en',
    )
    db_session.add_all([farmer, buyer])
    await db_session.flush()

    await ensure_wallet(db_session, farmer, welcome_bonus=True)
    await ensure_wallet(db_session, buyer)
    await credit_wallet(db_session, user=buyer, amount=Decimal('500'), description='Seed wallet for dispatch test.')

    listing = Listing(
        id=generate_id('LST'),
        farmer_id=farmer.id,
        crop_name='onion',
        quantity_kg=Decimal('40'),
        quantity_remaining=Decimal('40'),
        price_per_kg=Decimal('15'),
        currency='INR',
        market_type=ListingMarketType.LOCAL,
        pickup_type=PickupType.FARMER_DELIVERS,
        blockchain_hash='dispatch-hash',
    )
    db_session.add(listing)
    await db_session.flush()

    order = await place_order(db_session, buyer=buyer, listing=listing, quantity_kg=Decimal('10'))
    await db_session.flush()
    order.listing = listing
    order.listing.farmer = farmer
    order.buyer = buyer

    await mark_order_in_transit(db_session, order=order, farmer=farmer)
    await db_session.commit()

    refreshed = (await db_session.execute(select(Order).where(Order.id == order.id))).scalar_one()
    assert refreshed.status == OrderStatus.IN_TRANSIT
    assert refreshed.dispatched_at is not None

