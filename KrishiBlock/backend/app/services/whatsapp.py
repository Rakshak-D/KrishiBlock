from __future__ import annotations

import asyncio
import logging

from fastapi import Request
from twilio.request_validator import RequestValidator
from twilio.rest import Client

from app.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


class WhatsAppService:
    def __init__(self) -> None:
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN) if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN else None

    async def send_message(self, to: str, body: str, media_url: str | None = None) -> bool:
        if self.client is None or settings.sync_database_url.startswith('sqlite'):
            logger.info('Skipping live WhatsApp send to %s.', to)
            return False

        destination = to if to.startswith('whatsapp:') else f'whatsapp:{to}'
        payload: dict[str, object] = {
            'from_': settings.TWILIO_WHATSAPP_NUMBER,
            'to': destination,
            'body': body,
        }
        if media_url:
            full_media_url = media_url
            if media_url.startswith('/'):
                full_media_url = f"{settings.BASE_URL.rstrip('/')}" + media_url
            elif not media_url.startswith('http'):
                full_media_url = f"{settings.BASE_URL.rstrip('/')}" + f"/{media_url.lstrip('/')}"
            payload['media_url'] = [full_media_url]

        try:
            await asyncio.to_thread(self.client.messages.create, **payload)
            return True
        except Exception as exc:
            logger.exception('Failed to send WhatsApp message to %s: %s', destination, exc)
            return False


async def validate_twilio_signature(request: Request) -> bool:
    if not settings.TWILIO_AUTH_TOKEN:
        logger.warning('Twilio auth token is missing; rejecting webhook validation.')
        return False

    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    form = await request.form()
    signature = request.headers.get('X-Twilio-Signature', '')
    return validator.validate(str(request.url), dict(form), signature)


whatsapp_service = WhatsAppService()
