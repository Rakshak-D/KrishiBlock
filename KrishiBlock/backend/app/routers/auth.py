from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.user import MarketType, User, UserType
from app.schemas import OTPRequest, OTPVerifyRequest, RegisterRequest
from app.services.otp_service import request_otp, verify_otp_code
from app.services.session import increment_rate_limit
from app.services.wallet_service import ensure_wallet
from app.utils.id_generator import generate_user_id
from app.utils.security import create_access_token
from app.utils.serializers import envelope, serialize_datetime
from app.utils.validators import validate_name


settings = get_settings()
router = APIRouter(prefix='/api/auth', tags=['auth'])


def _user_payload(user: User) -> dict[str, object | None]:
    return {
        'id': user.id,
        'name': user.name,
        'phone': user.phone,
        'village': user.village,
        'user_type': user.user_type.value,
        'language': user.language,
        'market_type': user.market_type.value,
        'reputation_score': float(user.reputation_score),
        'created_at': serialize_datetime(user.created_at),
        'wallet_address': user.wallet_address,
    }


@router.post('/register')
async def register_route(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> dict[str, object | None]:
    count = await increment_rate_limit(payload.phone, 'auth-register', settings.RATE_LIMIT_WINDOW_SECONDS)
    if count > 5:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail='Too many registration attempts. Please wait a minute and try again.')

    existing_result = await db.execute(select(User).where(User.phone == payload.phone))
    existing_user = existing_result.scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='An account with this phone number already exists. Please sign in instead.')

    valid_name, cleaned_name = validate_name(payload.name)
    if not valid_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=cleaned_name)

    try:
        user_type = UserType(payload.user_type)
        market_type = MarketType(payload.market_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unsupported registration selection.') from exc

    user = User(
        id=await generate_user_id(db),
        phone=payload.phone,
        name=cleaned_name,
        village=payload.village,
        user_type=user_type,
        language=payload.language,
        market_type=market_type,
    )
    db.add(user)
    await db.flush()
    await ensure_wallet(db, user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, {'phone': user.phone})
    return envelope(
        {
            'token': token,
            'user': {
                'id': user.id,
                'name': user.name,
                'phone': user.phone,
                'village': user.village,
                'user_type': user.user_type.value,
                'language': user.language,
                'market_type': user.market_type.value,
                'wallet_address': user.wallet_address,
            },
            'onboarding': {
                'wallet_balance': float(settings.WELCOME_BONUS_AMOUNT),
                'message': 'Account created successfully. Your starter wallet is ready.',
            },
        }
    )


@router.post('/request-otp')
async def request_otp_route(payload: OTPRequest, db: AsyncSession = Depends(get_db)) -> dict[str, object | None]:
    count = await increment_rate_limit(payload.phone, 'auth-request-otp', settings.RATE_LIMIT_WINDOW_SECONDS)
    if count > 5:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail='Too many OTP requests. Please wait a minute and try again.')

    result = await db.execute(select(User).where(User.phone == payload.phone))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No KrishiBlock account was found for this phone number. Please create one first.')

    otp_result = await request_otp(payload.phone)
    response = {'message': 'OTP sent successfully.'}
    if otp_result.get('otp'):
        response['dev_otp'] = otp_result['otp']
    elif not otp_result.get('delivered'):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='OTP could not be delivered. Configure Twilio or switch to development mode.')
    return envelope(response)


@router.post('/verify-otp')
async def verify_otp_route(payload: OTPVerifyRequest, db: AsyncSession = Depends(get_db)) -> dict[str, object | None]:
    count = await increment_rate_limit(payload.phone, 'auth-verify-otp', settings.RATE_LIMIT_WINDOW_SECONDS)
    if count > 10:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail='Too many OTP verification attempts. Please wait a minute and try again.')

    valid, message = await verify_otp_code(payload.phone, payload.otp)
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    result = await db.execute(select(User).where(User.phone == payload.phone))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found.')

    token = create_access_token(user.id, {'phone': user.phone})
    return envelope({'token': token, 'user': _user_payload(user)})


@router.get('/me')
async def me(current_user: User = Depends(get_current_user)) -> dict[str, object | None]:
    return envelope(_user_payload(current_user))
