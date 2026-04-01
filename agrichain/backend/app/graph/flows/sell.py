from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.graph.state import ConversationState
from app.models.listing import Listing, ListingMarketType, PickupType
from app.models.user import MarketType, User
from app.services.blockchain_sim import hash_listing
from app.services.mandi_price import get_mandi_price
from app.services.notification import send_notification
from app.services.qr_service import generate_listing_qr, inr_to_usd
from app.utils.id_generator import generate_listing_id
from app.utils.i18n import CROP_OPTIONS, crop_menu, t
from app.utils.validators import validate_menu_choice, validate_price, validate_quantity


settings = get_settings()
PICKUP_MAP = {1: PickupType.AT_FARM, 2: PickupType.NEAREST_MANDI, 3: PickupType.FARMER_DELIVERS}


async def handle_sell_flow(state: ConversationState, message: str, db: AsyncSession, user: User) -> ConversationState:
    if state['flow_step'] == 0:
        valid, choice = validate_menu_choice(message, len(CROP_OPTIONS))
        if not valid:
            state['response'] = crop_menu(state['language'])
            return state
        state['temp'] = {'crop': CROP_OPTIONS[choice - 1]}
        state['flow_step'] = 1
        state['response'] = t('sell_ask_qty', state['language'])
        return state

    if state['flow_step'] == 1:
        valid, quantity, error = validate_quantity(message)
        if not valid:
            state['response'] = error
            return state
        mandi_price = await get_mandi_price(state['temp']['crop'])
        state['temp']['quantity_kg'] = f'{quantity:.2f}'
        state['temp']['mandi_price'] = f'{mandi_price:.2f}'
        state['flow_step'] = 2
        state['response'] = t('sell_ask_price', state['language'], mandi_price=f'{mandi_price:.2f}')
        return state

    if state['flow_step'] == 2:
        valid, price, error, warn = validate_price(message, state['temp']['crop'], float(state['temp']['mandi_price']))
        if not valid:
            state['response'] = error
            return state
        state['temp']['price_inr'] = f'{price:.2f}'
        if warn:
            state['flow_step'] = 21
            state['response'] = t('sell_price_warn', state['language'], price=f'{price:.2f}', mandi=state['temp']['mandi_price'])
            return state
        state['flow_step'] = 3
        state['response'] = t('sell_ask_pickup', state['language'])
        return state

    if state['flow_step'] == 21:
        if message.strip().upper() != 'YES':
            state['flow_step'] = 2
            state['response'] = t('sell_ask_price', state['language'], mandi_price=state['temp']['mandi_price'])
            return state
        state['flow_step'] = 3
        state['response'] = t('sell_ask_pickup', state['language'])
        return state

    if state['flow_step'] == 3:
        valid, choice = validate_menu_choice(message, 3)
        if not valid:
            state['response'] = t('sell_ask_pickup', state['language'])
            return state
        state['temp']['pickup_type'] = PICKUP_MAP[choice].value
        if user.market_type in {MarketType.GLOBAL, MarketType.BOTH}:
            state['flow_step'] = 4
            state['response'] = t('sell_ask_gi_tag', state['language'])
            return state
        state['temp']['gi_tag'] = ''
        state['flow_step'] = 5
        return await _build_summary(state, user)

    if state['flow_step'] == 4:
        state['temp']['gi_tag'] = '' if message.strip().upper() == 'SKIP' else message.strip()[:100]
        state['flow_step'] = 5
        return await _build_summary(state, user)

    if state['flow_step'] == 5:
        if message.strip().upper() != 'YES':
            state['current_flow'] = None
            state['flow_step'] = 0
            state['temp'] = {}
            state['response'] = t('action_cancelled', state['language'])
            return state

        listing_market = ListingMarketType.GLOBAL if user.market_type in {MarketType.GLOBAL, MarketType.BOTH} else ListingMarketType.LOCAL
        base_price_inr = Decimal(state['temp']['price_inr'])
        stored_price = inr_to_usd(base_price_inr) if listing_market == ListingMarketType.GLOBAL else base_price_inr
        currency = 'USD' if listing_market == ListingMarketType.GLOBAL else 'INR'
        quantity = Decimal(state['temp']['quantity_kg'])
        listing = Listing(
            id=await generate_listing_id(db),
            farmer_id=user.id,
            crop_name=state['temp']['crop'],
            quantity_kg=quantity,
            quantity_remaining=quantity,
            price_per_kg=stored_price,
            currency=currency,
            market_type=listing_market,
            pickup_type=PickupType(state['temp']['pickup_type']),
            gi_tag=state['temp'].get('gi_tag') or None,
            organic_certified=False,
            blockchain_hash=hash_listing(
                {
                    'farmer_id': user.id,
                    'crop_name': state['temp']['crop'],
                    'quantity_kg': quantity,
                    'price_per_kg': stored_price,
                    'currency': currency,
                    'market_type': listing_market.value,
                    'pickup_type': state['temp']['pickup_type'],
                    'gi_tag': state['temp'].get('gi_tag') or None,
                    'created_at': datetime.now(timezone.utc),
                }
            ),
        )
        db.add(listing)
        await db.flush()
        listing.qr_code_path = generate_listing_qr(listing, user)

        await send_notification(
            user.phone,
            'listing_created',
            {'crop': t(f'crop_{listing.crop_name}', user.language), 'listing_id': listing.id},
            user.language,
        )

        state['current_flow'] = None
        state['flow_step'] = 0
        state['temp'] = {}
        state['media_url'] = f"{settings.BASE_URL.rstrip('/')}" + f"/{listing.qr_code_path}"
        state['response'] = t(
            'sell_confirmed',
            state['language'],
            listing_id=listing.id,
            crop=t(f'crop_{listing.crop_name}', state['language']),
            qty=f'{listing.quantity_kg:.2f}',
            price=f'{listing.price_per_kg:.2f}',
            currency_symbol='$' if listing.currency == 'USD' else '₹',
        )
        return state

    state['response'] = crop_menu(state['language'])
    return state


async def _build_summary(state: ConversationState, user: User) -> ConversationState:
    is_global = user.market_type in {MarketType.GLOBAL, MarketType.BOTH}
    currency_symbol = '$' if is_global else '₹'
    display_price = f'{inr_to_usd(Decimal(state["temp"]["price_inr"])):.2f}' if is_global else state['temp']['price_inr']
    state['response'] = t(
        'sell_summary',
        state['language'],
        crop=t(f'crop_{state["temp"]["crop"]}', state['language']),
        qty=state['temp']['quantity_kg'],
        price=display_price,
        currency_symbol=currency_symbol,
        pickup=t(f'pickup_{state["temp"]["pickup_type"]}', state['language']),
        market=t(f'market_{"global" if is_global else "local"}', state['language']),
        gi_tag=state['temp'].get('gi_tag') or 'None',
    )
    return state
