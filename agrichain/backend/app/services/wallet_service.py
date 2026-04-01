from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.listing import Listing, ListingStatus, PickupType
from app.models.order import Order, OrderStatus
from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.models.wallet import Wallet, WithdrawalRequest, WithdrawalStatus
from app.services.blockchain_sim import chain_transaction, get_genesis_hash, verify_chain
from app.services.notification import send_notification
from app.utils.escrow import validate_release_key
from app.utils.id_generator import generate_order_id, generate_txn_id, generate_wallet_id, generate_withdrawal_id


settings = get_settings()
TWOPLACES = Decimal('0.01')


def _decimal(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


async def _last_hash(db: AsyncSession) -> str:
    result = await db.execute(select(Transaction.hash).order_by(Transaction.created_at.desc(), Transaction.id.desc()).limit(1))
    return result.scalar_one_or_none() or get_genesis_hash()


async def _reference_transactions(db: AsyncSession, order: Order) -> list[Transaction]:
    reference_ids = [order.id]
    if order.listing_id:
        reference_ids.append(order.listing_id)
    result = await db.execute(
        select(Transaction)
        .where(Transaction.reference_id.in_(reference_ids))
        .order_by(Transaction.created_at.asc(), Transaction.id.asc())
    )
    return result.scalars().all()


async def create_transaction(
    db: AsyncSession,
    *,
    user: User,
    tx_type: TransactionType,
    amount: Decimal,
    balance_after: Decimal,
    reference_id: str | None,
    description: str,
) -> Transaction:
    tx_id = await generate_txn_id(db)
    created_at = datetime.now(timezone.utc)
    payload = {
        'id': tx_id,
        'user_id': user.id,
        'type': tx_type.value,
        'amount': _decimal(amount),
        'balance_after': _decimal(balance_after),
        'reference_id': reference_id,
        'description': description,
        'created_at': created_at,
    }
    tx_hash = chain_transaction(await _last_hash(db), payload)
    transaction = Transaction(
        id=tx_id,
        user_id=user.id,
        type=tx_type,
        amount=_decimal(amount),
        balance_after=_decimal(balance_after),
        reference_id=reference_id,
        description=description,
        created_at=created_at,
        hash=tx_hash,
    )
    db.add(transaction)
    await db.flush()
    return transaction


async def ensure_wallet(db: AsyncSession, user: User, welcome_bonus: bool = False) -> Wallet:
    result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = result.scalar_one_or_none()
    if wallet is not None:
        return wallet

    wallet = Wallet(
        id=await generate_wallet_id(db),
        user_id=user.id,
        balance=_decimal(settings.WELCOME_BONUS_AMOUNT),
        locked_balance=_decimal(0),
        currency='INR',
    )
    db.add(wallet)
    await db.flush()
    await create_transaction(
        db,
        user=user,
        tx_type=TransactionType.WELCOME_BONUS,
        amount=_decimal(settings.WELCOME_BONUS_AMOUNT),
        balance_after=wallet.balance,
        reference_id=wallet.id,
        description='Welcome bonus credited to AgriChain wallet.',
    )
    return wallet


async def credit_wallet(
    db: AsyncSession,
    *,
    user: User,
    amount: Decimal,
    tx_type: TransactionType = TransactionType.CREDIT,
    reference_id: str | None = None,
    description: str,
) -> Wallet:
    wallet = await ensure_wallet(db, user)
    amount = _decimal(amount)
    if wallet.balance + amount > settings.MAX_WALLET_BALANCE:
        raise ValueError('Wallet balance limit exceeded.')
    wallet.balance = _decimal(wallet.balance + amount)
    await create_transaction(
        db,
        user=user,
        tx_type=tx_type,
        amount=amount,
        balance_after=wallet.balance,
        reference_id=reference_id,
        description=description,
    )
    return wallet


async def debit_wallet(
    db: AsyncSession,
    *,
    user: User,
    amount: Decimal,
    tx_type: TransactionType = TransactionType.DEBIT,
    reference_id: str | None = None,
    description: str,
) -> Wallet:
    wallet = await ensure_wallet(db, user)
    amount = _decimal(amount)
    if wallet.balance < amount:
        raise ValueError('Insufficient wallet balance.')
    wallet.balance = _decimal(wallet.balance - amount)
    await create_transaction(
        db,
        user=user,
        tx_type=tx_type,
        amount=amount,
        balance_after=wallet.balance,
        reference_id=reference_id,
        description=description,
    )
    return wallet


async def lock_escrow(db: AsyncSession, *, buyer: User, amount: Decimal, order: Order) -> Wallet:
    wallet = await ensure_wallet(db, buyer)
    amount = _decimal(amount)
    if wallet.balance < amount:
        raise ValueError('Insufficient wallet balance.')

    wallet.balance = _decimal(wallet.balance - amount)
    await create_transaction(
        db,
        user=buyer,
        tx_type=TransactionType.DEBIT,
        amount=amount,
        balance_after=wallet.balance,
        reference_id=order.id,
        description=f'Wallet debited for order {order.id}.',
    )

    wallet.locked_balance = _decimal(wallet.locked_balance + amount)
    await create_transaction(
        db,
        user=buyer,
        tx_type=TransactionType.ESCROW_LOCK,
        amount=amount,
        balance_after=wallet.balance,
        reference_id=order.id,
        description=f'Escrow locked for order {order.id}.',
    )
    return wallet


async def release_escrow(db: AsyncSession, *, order: Order, farmer: User, buyer: User) -> None:
    buyer_wallet = await ensure_wallet(db, buyer)
    farmer_wallet = await ensure_wallet(db, farmer)
    total_amount = _decimal(order.total_amount)
    platform_fee = _decimal(order.platform_fee)
    farmer_payout = _decimal(total_amount - platform_fee)

    if buyer_wallet.locked_balance < total_amount:
        raise ValueError('Escrow balance is lower than the order total.')

    buyer_wallet.locked_balance = _decimal(buyer_wallet.locked_balance - total_amount)
    await create_transaction(
        db,
        user=buyer,
        tx_type=TransactionType.ESCROW_RELEASE,
        amount=total_amount,
        balance_after=buyer_wallet.balance,
        reference_id=order.id,
        description=f'Escrow released for delivered order {order.id}.',
    )

    farmer_wallet.balance = _decimal(farmer_wallet.balance + farmer_payout)
    await create_transaction(
        db,
        user=farmer,
        tx_type=TransactionType.ESCROW_RELEASE,
        amount=farmer_payout,
        balance_after=farmer_wallet.balance,
        reference_id=order.id,
        description=f'Escrow payout received for delivered order {order.id}.',
    )
    await create_transaction(
        db,
        user=farmer,
        tx_type=TransactionType.FEE,
        amount=platform_fee,
        balance_after=farmer_wallet.balance,
        reference_id=order.id,
        description=f'Platform fee retained for order {order.id}.',
    )

    farmer.reputation_score = min(Decimal('5.00'), _decimal(farmer.reputation_score + Decimal('0.05')))

    await send_notification(farmer.phone, 'delivery_confirmed', {'amount': f'{farmer_payout:.2f}', 'order_id': order.id}, farmer.language)
    await send_notification(buyer.phone, 'delivery_recorded', {'amount': f'{total_amount:.2f}', 'order_id': order.id}, buyer.language)


async def create_withdrawal(db: AsyncSession, *, user: User, amount: Decimal, upi_id: str) -> WithdrawalRequest:
    amount = _decimal(amount)
    withdrawal_id = await generate_withdrawal_id(db)
    await debit_wallet(
        db,
        user=user,
        amount=amount,
        tx_type=TransactionType.DEBIT,
        reference_id=withdrawal_id,
        description=f'Withdrawal processing to {upi_id}.',
    )
    withdrawal = WithdrawalRequest(
        id=withdrawal_id,
        user_id=user.id,
        amount=amount,
        upi_id=upi_id,
        status=WithdrawalStatus.PROCESSING,
    )
    db.add(withdrawal)
    await db.flush()
    return withdrawal


async def place_order(db: AsyncSession, *, buyer: User, listing: Listing, quantity_kg: Decimal) -> Order:
    quantity = _decimal(quantity_kg)
    if listing.quantity_remaining is None or listing.quantity_remaining < quantity:
        raise ValueError('Requested quantity is higher than available stock.')

    total = _decimal(quantity * listing.price_per_kg)
    fee = _decimal(total * settings.PLATFORM_FEE_PERCENT / Decimal('100'))
    order = Order(
        id=await generate_order_id(db),
        listing_id=listing.id,
        buyer_id=buyer.id,
        quantity_kg=quantity,
        total_amount=total,
        platform_fee=fee,
        status=OrderStatus.ESCROW_LOCKED,
    )
    db.add(order)
    await db.flush()

    listing.quantity_remaining = _decimal(listing.quantity_remaining - quantity)
    if listing.quantity_remaining <= 0:
        listing.quantity_remaining = _decimal(0)
        listing.status = ListingStatus.SOLD
    elif listing.quantity_remaining < listing.quantity_kg:
        listing.status = ListingStatus.PARTIALLY_SOLD

    await lock_escrow(db, buyer=buyer, amount=total, order=order)
    return order


async def mark_order_in_transit(db: AsyncSession, *, order: Order, farmer: User) -> Order:
    if order.listing is None or order.listing.farmer is None:
        result = await db.execute(
            select(Order)
            .where(Order.id == order.id)
            .options(selectinload(Order.listing).selectinload(Listing.farmer), selectinload(Order.buyer))
        )
        order = result.scalar_one()

    if order.listing.farmer_id != farmer.id:
        raise ValueError('This order does not belong to your listings.')
    if order.status != OrderStatus.ESCROW_LOCKED:
        raise ValueError('Only escrow locked orders can be moved to in transit.')

    order.status = OrderStatus.IN_TRANSIT
    order.dispatched_at = datetime.now(timezone.utc)
    order.notes = 'Farmer marked this order as dispatched.'
    await send_notification(
        order.buyer.phone,
        'order_dispatched',
        {'order_id': order.id, 'crop': order.listing.crop_name.title()},
        order.buyer.language,
    )
    return order


async def update_listing(
    db: AsyncSession,
    *,
    listing: Listing,
    farmer: User,
    quantity_kg: Decimal | None = None,
    price_per_kg: Decimal | None = None,
    pickup_type: str | None = None,
    gi_tag: str | None = None,
    organic_certified: bool | None = None,
) -> Listing:
    if listing.farmer_id != farmer.id:
        raise ValueError('This listing does not belong to you.')
    if listing.status not in {ListingStatus.ACTIVE, ListingStatus.PARTIALLY_SOLD}:
        raise ValueError('Only active listings can be updated.')

    sold_quantity = _decimal(listing.quantity_kg - (listing.quantity_remaining or Decimal('0.00')))
    if quantity_kg is not None:
        new_quantity = _decimal(quantity_kg)
        if new_quantity < sold_quantity:
            raise ValueError('Updated quantity cannot be lower than the already sold quantity.')
        listing.quantity_remaining = _decimal(new_quantity - sold_quantity)
        listing.quantity_kg = new_quantity
        if listing.quantity_remaining <= 0:
            listing.quantity_remaining = _decimal(0)
            listing.status = ListingStatus.SOLD
        elif sold_quantity > 0:
            listing.status = ListingStatus.PARTIALLY_SOLD
        else:
            listing.status = ListingStatus.ACTIVE
    if price_per_kg is not None:
        listing.price_per_kg = _decimal(price_per_kg)
    if pickup_type is not None:
        listing.pickup_type = PickupType(pickup_type)
    if gi_tag is not None:
        listing.gi_tag = gi_tag or None
    if organic_certified is not None:
        listing.organic_certified = organic_certified
    return listing


async def cancel_listing(db: AsyncSession, *, listing: Listing, farmer: User) -> Listing:
    if listing.farmer_id != farmer.id:
        raise ValueError('This listing does not belong to you.')
    if listing.status not in {ListingStatus.ACTIVE, ListingStatus.PARTIALLY_SOLD}:
        raise ValueError('Only active listings can be cancelled.')

    active_order_result = await db.execute(
        select(func.count(Order.id)).where(
            Order.listing_id == listing.id,
            Order.status.in_([OrderStatus.ESCROW_LOCKED, OrderStatus.IN_TRANSIT]),
        )
    )
    if int(active_order_result.scalar_one()) > 0:
        raise ValueError('This listing has active orders and cannot be cancelled yet.')

    listing.status = ListingStatus.CANCELLED
    return listing


async def confirm_order_delivery(db: AsyncSession, *, order: Order, buyer: User, release_key: str | None = None) -> Order:
    if order.buyer_id != buyer.id:
        raise ValueError('This order does not belong to you.')
    if order.status not in {OrderStatus.ESCROW_LOCKED, OrderStatus.IN_TRANSIT}:
        raise ValueError('Only active shipped orders can be confirmed.')

    if order.listing is None or order.listing.farmer is None:
        result = await db.execute(
            select(Order)
            .where(Order.id == order.id)
            .options(selectinload(Order.listing).selectinload(Listing.farmer), selectinload(Order.buyer))
        )
        order = result.scalar_one()

    if release_key is not None and not validate_release_key(order.listing, order, release_key):
        raise ValueError('Release key is invalid. Please use the key shared by the farmer at handoff.')

    ledger_result = await db.execute(select(Transaction).order_by(Transaction.created_at.asc(), Transaction.id.asc()))
    normalized = [
        {
            'id': tx.id,
            'user_id': tx.user_id,
            'type': tx.type.value,
            'amount': tx.amount,
            'balance_after': tx.balance_after,
            'reference_id': tx.reference_id,
            'description': tx.description,
            'created_at': tx.created_at,
            'hash': tx.hash,
        }
        for tx in ledger_result.scalars().all()
    ]
    if not verify_chain(normalized):
        raise ValueError('The product ledger could not be verified, so escrow release is blocked.')

    order.status = OrderStatus.DELIVERED
    order.delivery_confirmed_at = datetime.now(timezone.utc)
    await release_escrow(db, order=order, farmer=order.listing.farmer, buyer=buyer)
    return order


async def expire_listings(db: AsyncSession) -> int:
    result = await db.execute(
        select(Listing)
        .where(
            Listing.status.in_([ListingStatus.ACTIVE, ListingStatus.PARTIALLY_SOLD]),
            Listing.expires_at <= datetime.now(timezone.utc),
        )
        .options(selectinload(Listing.farmer))
    )
    expired_count = 0
    for listing in result.scalars().all():
        listing.status = ListingStatus.EXPIRED
        expired_count += 1
        remaining = listing.quantity_remaining or Decimal('0.00')
        await send_notification(
            listing.farmer.phone,
            'listing_expiring',
            {'crop': listing.crop_name.title(), 'qty': f'{remaining:.2f}'},
            listing.farmer.language,
        )
    return expired_count


async def process_withdrawals(db: AsyncSession) -> int:
    result = await db.execute(
        select(WithdrawalRequest)
        .where(WithdrawalRequest.status == WithdrawalStatus.PROCESSING)
        .options(selectinload(WithdrawalRequest.user))
    )
    processed = 0
    threshold = datetime.now(timezone.utc) - timedelta(minutes=30)
    for withdrawal in result.scalars().all():
        if withdrawal.created_at <= threshold:
            withdrawal.status = WithdrawalStatus.COMPLETED
            withdrawal.completed_at = datetime.now(timezone.utc)
            processed += 1
    return processed


