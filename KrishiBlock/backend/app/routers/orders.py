from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models.listing import Listing
from app.models.order import Order
from app.models.user import User
from app.schemas import OrderConfirmRequest
from app.services.wallet_service import confirm_order_delivery
from app.utils.serializers import envelope


router = APIRouter(prefix='/api/orders', tags=['orders'])


@router.post('/{order_id}/confirm')
async def confirm_delivery(
    order_id: str,
    payload: OrderConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object | None]:
    result = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.listing).selectinload(Listing.farmer), selectinload(Order.buyer))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found.')
    try:
        await confirm_order_delivery(db, order=order, buyer=current_user, release_key=payload.release_key)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    return envelope({'message': f'Order {order.id} confirmed successfully.'})
