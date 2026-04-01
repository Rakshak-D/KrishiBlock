from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.graph.state import ConversationState
from app.models.listing import Listing, ListingStatus
from app.models.user import User
from app.services.notification import send_notification
from app.services.wallet_service import ensure_wallet, place_order
from app.utils.i18n import CROP_OPTIONS, crop_menu, t
from app.utils.validators import validate_menu_choice, validate_quantity


settings = get_settings()


def _resolve_crop_choice(message: str) -> str | None:
    valid, choice = validate_menu_choice(message, len(CROP_OPTIONS))
    if valid:
        return CROP_OPTIONS[choice - 1]
    normalized = message.strip().lower()
    if normalized in CROP_OPTIONS:
        return normalized
    return None


async def handle_buy_flow(state: ConversationState, message: str, db: AsyncSession, user: User) -> ConversationState:
    if state['flow_step'] == 0:
        crop = _resolve_crop_choice(message)
        if crop is None:
            state['response'] = crop_menu(state['language'])
            return state
        state['temp'] = {'crop': crop}
        result = await db.execute(
            select(Listing)
            .where(Listing.crop_name == crop, Listing.status.in_([ListingStatus.ACTIVE, ListingStatus.PARTIALLY_SOLD]))
            .options(selectinload(Listing.farmer))
            .order_by(Listing.price_per_kg.asc(), Listing.created_at.desc())
            .limit(3)
        )
        listings = result.scalars().all()
        if not listings:
            state['response'] = t('buy_no_listings', state['language'], crop=t(f'crop_{crop}', state['language']))
            return state

        state['temp']['listing_ids'] = ','.join(listing.id for listing in listings)
        options = []
        for index, listing in enumerate(listings, start=1):
            options.append(
                f'{index}. {listing.farmer.name} | {listing.farmer.village or "-"} | rating {listing.farmer.reputation_score} | {listing.quantity_remaining:.2f}kg | {listing.currency} {listing.price_per_kg:.2f}'
            )
        state['flow_step'] = 1
        state['response'] = t('buy_listings', state['language'], crop=t(f'crop_{crop}', state['language']), options='\n'.join(options))
        return state

    if state['flow_step'] == 1:
        listing_ids = [identifier for identifier in str(state['temp'].get('listing_ids', '')).split(',') if identifier]
        valid, choice = validate_menu_choice(message, len(listing_ids))
        if not valid:
            state['response'] = t('buy_invalid_listing', state['language'])
            return state
        listing_id = listing_ids[choice - 1]
        result = await db.execute(select(Listing).where(Listing.id == listing_id).options(selectinload(Listing.farmer)))
        listing = result.scalar_one_or_none()
        if listing is None:
            state['response'] = t('buy_listing_missing', state['language'])
            return state
        state['temp']['listing_id'] = listing.id
        state['temp']['listing_qty'] = f'{listing.quantity_remaining:.2f}'
        state['flow_step'] = 2
        state['response'] = t('buy_ask_qty', state['language'], max_qty=f'{listing.quantity_remaining:.2f}')
        return state

    if state['flow_step'] == 2:
        valid, quantity, error = validate_quantity(message)
        if not valid:
            state['response'] = error
            return state
        if Decimal(str(quantity)) > Decimal(str(state['temp']['listing_qty'])):
            state['response'] = t('buy_quantity_too_high', state['language'], max_qty=str(state['temp']['listing_qty']))
            return state
        result = await db.execute(select(Listing).where(Listing.id == state['temp']['listing_id']).options(selectinload(Listing.farmer)))
        listing = result.scalar_one()
        total = (Decimal(str(quantity)) * listing.price_per_kg).quantize(Decimal('0.01'))
        fee = (total * settings.PLATFORM_FEE_PERCENT / Decimal('100')).quantize(Decimal('0.01'))
        wallet = await ensure_wallet(db, user)

        state['temp']['quantity_kg'] = f'{quantity:.2f}'
        state['temp']['unit_price'] = f'{listing.price_per_kg:.2f}'
        state['temp']['total_amount'] = f'{total:.2f}'
        state['temp']['platform_fee'] = f'{fee:.2f}'
        state['temp']['currency'] = listing.currency
        state['temp']['farmer_name'] = listing.farmer.name

        if wallet.balance < total:
            state['flow_step'] = 21
            state['temp']['required_amount'] = f'{total:.2f}'
            state['response'] = t('insufficient_balance', state['language'], balance=f'{wallet.balance:.2f}', required=f'{total:.2f}') + '\n1. Add money\n2. Cancel'
            return state
        state['flow_step'] = 3
        state['response'] = t(
            'buy_summary',
            state['language'],
            crop=t(f'crop_{listing.crop_name}', state['language']),
            qty=f'{quantity:.2f}',
            farmer=listing.farmer.name,
            price=f'{listing.price_per_kg:.2f}',
            total=f'{total:.2f}',
            fee=f'{fee:.2f}',
            currency_symbol='$' if listing.currency == 'USD' else '₹',
        )
        return state

    if state['flow_step'] == 21:
        if message.strip() == '1':
            resume_state = {
                'crop': state['temp']['crop'],
                'listing_id': state['temp']['listing_id'],
                'listing_qty': state['temp']['listing_qty'],
                'quantity_kg': state['temp']['quantity_kg'],
                'unit_price': state['temp']['unit_price'],
                'total_amount': state['temp']['total_amount'],
                'platform_fee': state['temp']['platform_fee'],
                'currency': state['temp']['currency'],
                'farmer_name': state['temp']['farmer_name'],
            }
            state['current_flow'] = 'wallet'
            state['flow_step'] = 1
            state['temp'] = {'mode': 'add', 'resume_flow': 'buy', 'resume_state': resume_state}
            state['response'] = t('wallet_add_ask_amount', state['language'])
            return state
        state['current_flow'] = None
        state['flow_step'] = 0
        state['temp'] = {}
        state['response'] = t('action_cancelled', state['language'])
        return state

    if state['flow_step'] == 3:
        if message.strip().upper() != 'YES':
            state['current_flow'] = None
            state['flow_step'] = 0
            state['temp'] = {}
            state['response'] = t('action_cancelled', state['language'])
            return state

        result = await db.execute(select(Listing).where(Listing.id == state['temp']['listing_id']).options(selectinload(Listing.farmer)))
        listing = result.scalar_one()
        order = await place_order(db, buyer=user, listing=listing, quantity_kg=Decimal(str(state['temp']['quantity_kg'])))

        await send_notification(
            listing.farmer.phone,
            'order_placed',
            {
                'buyer_city': user.village or 'buyer city',
                'qty': str(state['temp']['quantity_kg']),
                'crop': t(f'crop_{listing.crop_name}', listing.farmer.language),
            },
            listing.farmer.language,
        )
        await send_notification(
            listing.farmer.phone,
            'escrow_locked',
            {'amount': f'{order.total_amount:.2f}', 'deadline': '72 hours'},
            listing.farmer.language,
        )

        state['current_flow'] = None
        state['flow_step'] = 0
        state['temp'] = {}
        state['response'] = '\n'.join(
            [
                t('buy_escrow_locked', state['language'], order_id=order.id, amount=f'{order.total_amount:.2f}'),
                t('buy_confirm_instruction', state['language'], order_id=order.id),
            ]
        )
        return state

    state['response'] = crop_menu(state['language'])
    return state
