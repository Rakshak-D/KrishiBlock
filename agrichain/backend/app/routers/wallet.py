from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas import WalletAddRequest, WalletWithdrawRequest
from app.services.notification import send_notification
from app.services.session import increment_rate_limit
from app.services.wallet_service import create_withdrawal, credit_wallet, ensure_wallet
from app.utils.serializers import decimal_to_float, envelope, serialize_datetime
from app.utils.validators import validate_amount, validate_upi


settings = get_settings()
router = APIRouter(prefix='/api/dashboard/wallet', tags=['wallet'])


@router.get('')
async def get_wallet(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict[str, object | None]:
    wallet = await ensure_wallet(db, current_user)
    result = await db.execute(select(Transaction).where(Transaction.user_id == current_user.id).order_by(Transaction.created_at.desc()).limit(5))
    recent = [
        {
            'id': tx.id,
            'type': tx.type.value,
            'amount': decimal_to_float(tx.amount),
            'reference_id': tx.reference_id,
            'balance_after': decimal_to_float(tx.balance_after),
            'created_at': serialize_datetime(tx.created_at),
        }
        for tx in result.scalars().all()
    ]
    return envelope({'balance': decimal_to_float(wallet.balance), 'locked_balance': decimal_to_float(wallet.locked_balance), 'recent_transactions': recent})


@router.post('/add')
async def add_wallet_money(
    payload: WalletAddRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    count = await increment_rate_limit(current_user.phone, 'wallet-add', settings.RATE_LIMIT_WINDOW_SECONDS)
    if count > 10:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail='Too many wallet top-up attempts. Please wait a minute and try again.')

    valid, amount, error = validate_amount(str(payload.amount), float(settings.MIN_ADD_AMOUNT), float(settings.MAX_WALLET_BALANCE))
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    try:
        wallet = await credit_wallet(db, user=current_user, amount=Decimal(str(amount)), description='Simulated wallet top-up from dashboard.')
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    await send_notification(current_user.phone, 'wallet_credited', {'amount': f'{amount:.2f}', 'balance': f'{wallet.balance:.2f}'}, current_user.language)
    return envelope({'message': 'Simulated payment link sent and wallet credited.', 'balance': decimal_to_float(wallet.balance)})


@router.post('/withdraw')
async def withdraw_wallet_money(
    payload: WalletWithdrawRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    count = await increment_rate_limit(current_user.phone, 'wallet-withdraw', settings.RATE_LIMIT_WINDOW_SECONDS)
    if count > 8:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail='Too many withdrawal attempts. Please wait a minute and try again.')

    if not validate_upi(payload.upi_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Please enter a valid UPI ID.')
    valid, amount, error = validate_amount(str(payload.amount), float(settings.MIN_ADD_AMOUNT), float(settings.MAX_WALLET_BALANCE), current_balance=float((await ensure_wallet(db, current_user)).balance))
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    try:
        withdrawal = await create_withdrawal(db, user=current_user, amount=Decimal(str(amount)), upi_id=payload.upi_id)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    return envelope({'message': f'₹{withdrawal.amount:.2f} will reach your UPI in 1-2 hours (simulated).', 'withdrawal_id': withdrawal.id, 'status': withdrawal.status.value})
