from __future__ import annotations

import phonenumbers
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.services.conversation import conversation_engine
from app.services.session import clear_session, increment_rate_limit, load_session, save_session
from app.services.whatsapp import validate_twilio_signature, whatsapp_service
from app.utils.serializers import envelope


settings = get_settings()
router = APIRouter(prefix='/api', tags=['webhook'])


def _normalize_phone(value: str) -> str:
    candidate = value.strip()
    try:
        parsed = phonenumbers.parse(candidate, 'IN')
        if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
            raise ValueError
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception as exc:
        raise ValueError('Enter a valid phone number.') from exc


class SimulatedMessageRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=20)
    message: str = Field(min_length=1, max_length=1000)

    @field_validator('phone')
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return _normalize_phone(value)

    @field_validator('message')
    @classmethod
    def normalize_message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError('Enter a message to simulate.')
        return cleaned


class SimulatedPhoneRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=20)

    @field_validator('phone')
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return _normalize_phone(value)


@router.post('/webhook/whatsapp')
async def whatsapp_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    if not await validate_twilio_signature(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invalid Twilio signature.')

    form_data = await request.form()
    phone = str(form_data.get('From', '')).replace('whatsapp:', '')
    message = str(form_data.get('Body', '')).strip()
    if not phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Missing sender phone number.')

    count = await increment_rate_limit(phone, 'whatsapp', settings.RATE_LIMIT_WINDOW_SECONDS)
    if count > settings.MESSAGE_RATE_LIMIT:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail='You are sending messages too quickly. Please wait a minute.')

    session = await load_session(phone)
    result = await conversation_engine.process(phone, message, session, db)
    await save_session(phone, result['state'])
    await whatsapp_service.send_message(to=phone, body=str(result['response']), media_url=result.get('media_url'))
    return Response(content='', status_code=status.HTTP_200_OK, media_type='text/plain')


@router.post('/webhook/simulate')
async def simulate_whatsapp_message(payload: SimulatedMessageRequest, db: AsyncSession = Depends(get_db)) -> dict[str, object | None]:
    count = await increment_rate_limit(payload.phone, 'simulate', settings.RATE_LIMIT_WINDOW_SECONDS)
    if count > settings.MESSAGE_RATE_LIMIT:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail='You are sending messages too quickly. Please wait a minute.')

    session = await load_session(payload.phone)
    result = await conversation_engine.process(payload.phone, payload.message, session, db)
    await save_session(payload.phone, result['state'])
    return envelope({'response': result['response'], 'media_url': result.get('media_url'), 'state': result['state']})


@router.post('/webhook/simulate/reset')
async def reset_simulated_session(payload: SimulatedPhoneRequest) -> dict[str, object | None]:
    await clear_session(payload.phone)
    return envelope({'message': 'Conversation session cleared.'})


@router.get('/health')
async def health() -> dict[str, object | None]:
    return envelope({'status': 'ok'})

