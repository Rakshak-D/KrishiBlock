from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.models.listing import Listing, ListingMarketType, PickupType
from app.models.user import MarketType, User, UserType
from app.services.session import memory_store
from app.services.wallet_service import ensure_wallet
from app.utils.escrow import build_release_key
from app.utils.id_generator import generate_id
from app.utils.security import create_access_token


async def _fake_mandi_price(_crop: str, _state: str = 'Karnataka') -> float:
    return 24.0


@pytest_asyncio.fixture
async def api_client(monkeypatch):
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        monkeypatch.setattr('app.routers.listings.get_mandi_price', _fake_mandi_price)
        monkeypatch.setattr('app.routers.dashboard.get_mandi_price', _fake_mandi_price)
        monkeypatch.setattr('app.routers.dashboard.generate_listing_qr', lambda *_args, **_kwargs: '/static/qr/test.png')

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url='http://testserver') as client:
            yield client, session, monkeypatch

    app.dependency_overrides.clear()
    memory_store.clear()
    await engine.dispose()


async def _seed_user(session, *, phone: str, name: str, user_type: UserType, market_type: MarketType, village: str = 'Mandya') -> User:
    user = User(
        id=generate_id('AGR'),
        phone=phone,
        name=name,
        village=village,
        user_type=user_type,
        market_type=market_type,
        language='en',
    )
    session.add(user)
    await session.flush()
    await ensure_wallet(session, user)
    await session.commit()
    await session.refresh(user)
    return user


async def _seed_listing(session, farmer: User, *, market_type: ListingMarketType = ListingMarketType.LOCAL, crop_name: str = 'tomato') -> Listing:
    listing = Listing(
        id=generate_id('LST'),
        farmer_id=farmer.id,
        crop_name=crop_name,
        quantity_kg=Decimal('50.00'),
        quantity_remaining=Decimal('50.00'),
        price_per_kg=Decimal('20.00') if market_type == ListingMarketType.LOCAL else Decimal('1.25'),
        currency='INR' if market_type == ListingMarketType.LOCAL else 'USD',
        market_type=market_type,
        pickup_type=PickupType.AT_FARM,
        qr_code_path='/static/qr/test.png',
        blockchain_hash='test-hash',
        organic_certified=True,
    )
    session.add(listing)
    await session.commit()
    await session.refresh(listing)
    return listing


def _headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, {'phone': user.phone})
    return {'Authorization': f'Bearer {token}'}


@pytest.mark.asyncio
async def test_public_routes_and_auth_registration(api_client):
    client, session, _monkeypatch = api_client
    farmer = await _seed_user(
        session,
        phone='+919999100001',
        name='Farmer Public',
        user_type=UserType.FARMER,
        market_type=MarketType.BOTH,
    )
    local_listing = await _seed_listing(session, farmer, market_type=ListingMarketType.LOCAL, crop_name='tomato')
    await _seed_listing(session, farmer, market_type=ListingMarketType.GLOBAL, crop_name='ginger')

    health_response = await client.get('/api/health')
    assert health_response.status_code == 200
    assert health_response.json()['data']['status'] == 'ok'

    register_response = await client.post(
        '/api/auth/register',
        json={
            'phone': '+919999100011',
            'name': 'Buyer Public',
            'village': 'Mysuru',
            'user_type': 'buyer',
            'language': 'en',
            'market_type': 'local',
        },
    )
    assert register_response.status_code == 200
    register_data = register_response.json()['data']
    assert register_data['user']['user_type'] == 'buyer'

    me_response = await client.get('/api/auth/me', headers={'Authorization': f"Bearer {register_data['token']}"})
    assert me_response.status_code == 200
    assert me_response.json()['data']['phone'] == '+919999100011'

    duplicate_response = await client.post(
        '/api/auth/register',
        json={
            'phone': '+919999100011',
            'name': 'Buyer Public',
            'village': 'Mysuru',
            'user_type': 'buyer',
            'language': 'en',
            'market_type': 'local',
        },
    )
    assert duplicate_response.status_code == 409

    listings_response = await client.get('/api/listings')
    assert listings_response.status_code == 200
    assert listings_response.json()['data']['items']

    global_response = await client.get('/api/listings/global')
    assert global_response.status_code == 200
    assert global_response.json()['data']['items'][0]['market_type'] == 'global'

    overview_response = await client.get('/api/listings/overview')
    assert overview_response.status_code == 200
    assert overview_response.json()['data']['by_market']['local']['listing_count'] >= 1

    insights_response = await client.get('/api/listings/insights', params={'crop': 'tomato', 'market_type': 'local'})
    assert insights_response.status_code == 200
    assert insights_response.json()['data']['pricing_position'] in {'below_reference', 'above_reference', 'within_reference_band'}

    detail_response = await client.get(f'/api/listings/{local_listing.id}')
    assert detail_response.status_code == 200
    assert detail_response.json()['data']['id'] == local_listing.id

    verify_response = await client.get(f'/api/verify/{local_listing.id}')
    assert verify_response.status_code == 200
    assert verify_response.json()['data']['listing_id'] == local_listing.id


@pytest.mark.asyncio
async def test_dashboard_wallet_and_order_lifecycle_routes(api_client):
    client, session, _monkeypatch = api_client
    farmer = await _seed_user(
        session,
        phone='+919999100021',
        name='Farmer Routes',
        user_type=UserType.FARMER,
        market_type=MarketType.BOTH,
    )
    buyer = await _seed_user(
        session,
        phone='+919999100022',
        name='Buyer Routes',
        user_type=UserType.BUYER,
        market_type=MarketType.LOCAL,
        village='Bengaluru',
    )

    unauthorized = await client.get('/api/dashboard/overview')
    assert unauthorized.status_code == 401

    create_response = await client.post(
        '/api/dashboard/listings',
        headers=_headers(farmer),
        json={
            'crop_name': 'tomato',
            'quantity_kg': 40,
            'price_per_kg': 22,
            'pickup_type': 'at_farm',
            'market_type': 'local',
            'gi_tag': 'Mandya Tomato',
            'organic_certified': True,
        },
    )
    assert create_response.status_code == 200
    listing_id = create_response.json()['data']['id']

    farmer_listings = await client.get('/api/dashboard/listings', headers=_headers(farmer))
    assert farmer_listings.status_code == 200
    assert farmer_listings.json()['data']['items'][0]['id'] == listing_id

    update_response = await client.patch(
        f'/api/dashboard/listings/{listing_id}',
        headers=_headers(farmer),
        json={'price_per_kg': 24},
    )
    assert update_response.status_code == 200
    assert update_response.json()['data']['listing']['price_per_kg'] == 24.0

    wallet_add_response = await client.post('/api/dashboard/wallet/add', headers=_headers(buyer), json={'amount': 500})
    assert wallet_add_response.status_code == 200

    wallet_response = await client.get('/api/dashboard/wallet', headers=_headers(buyer))
    assert wallet_response.status_code == 200
    assert wallet_response.json()['data']['balance'] >= 600.0

    buy_response = await client.post(f'/api/listings/{listing_id}/buy', headers=_headers(buyer), json={'quantity_kg': 10})
    assert buy_response.status_code == 200
    order_id = buy_response.json()['data']['order_id']

    buyer_orders = await client.get('/api/dashboard/orders', headers=_headers(buyer))
    assert buyer_orders.status_code == 200
    assert buyer_orders.json()['data']['items'][0]['id'] == order_id

    incoming_response = await client.get('/api/dashboard/incoming-orders', headers=_headers(farmer))
    assert incoming_response.status_code == 200
    incoming_item = incoming_response.json()['data']['items'][0]
    release_key = incoming_item['release_key']
    assert incoming_item['id'] == order_id

    dispatch_response = await client.post(f'/api/dashboard/orders/{order_id}/dispatch', headers=_headers(farmer))
    assert dispatch_response.status_code == 200
    assert dispatch_response.json()['data']['status'] == 'in_transit'

    confirm_response = await client.post(
        f'/api/dashboard/orders/{order_id}/confirm',
        headers=_headers(buyer),
        json={},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()['data']['status'] == 'delivered'

    dashboard_overview = await client.get('/api/dashboard/overview', headers=_headers(buyer))
    assert dashboard_overview.status_code == 200
    assert dashboard_overview.json()['data']['metrics']['delivered_orders'] >= 1

    transactions_response = await client.get('/api/dashboard/transactions', headers=_headers(buyer))
    assert transactions_response.status_code == 200
    assert transactions_response.json()['data']['items']

    withdrawal_response = await client.post(
        '/api/dashboard/wallet/withdraw',
        headers=_headers(buyer),
        json={'amount': 50, 'upi_id': 'buyer@upi'},
    )
    assert withdrawal_response.status_code == 200

    second_create_response = await client.post(
        '/api/dashboard/listings',
        headers=_headers(farmer),
        json={
            'crop_name': 'onion',
            'quantity_kg': 20,
            'price_per_kg': 16,
            'pickup_type': 'nearest_mandi',
            'market_type': 'local',
            'organic_certified': False,
        },
    )
    second_listing_id = second_create_response.json()['data']['id']
    cancel_response = await client.post(f'/api/dashboard/listings/{second_listing_id}/cancel', headers=_headers(farmer))
    assert cancel_response.status_code == 200
    assert cancel_response.json()['data']['listing']['status'] == 'cancelled'


@pytest.mark.asyncio
async def test_webhook_simulation_routes(api_client):
    client, _session, monkeypatch = api_client

    async def fake_process(phone, message, state, _db):
        new_state = {**state, 'phone': phone, 'last_message': message}
        return {'response': f'ECHO: {message}', 'state': new_state, 'media_url': None}

    monkeypatch.setattr('app.routers.webhook.conversation_engine.process', fake_process)

    invalid_simulation = await client.post('/api/webhook/simulate', json={'phone': 'bad-number', 'message': 'HI'})
    assert invalid_simulation.status_code == 422

    simulation_response = await client.post('/api/webhook/simulate', json={'phone': '+919999100031', 'message': ' HI '})
    assert simulation_response.status_code == 200
    assert simulation_response.json()['data']['response'] == 'ECHO: HI'

    reset_response = await client.post('/api/webhook/simulate/reset', json={'phone': '+919999100031'})
    assert reset_response.status_code == 200
    assert reset_response.json()['data']['message'] == 'Conversation session cleared.'

    webhook_response = await client.post('/api/webhook/whatsapp', data={'From': 'whatsapp:+919999100031', 'Body': 'HI'})
    assert webhook_response.status_code == 403


