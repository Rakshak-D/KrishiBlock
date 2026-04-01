from __future__ import annotations

from app.services.whatsapp import whatsapp_service
from app.utils.i18n import t


NOTIFICATION_KEYS = {
    'listing_created': 'notification_listing_created',
    'order_placed': 'notification_order_placed',
    'escrow_locked': 'notification_escrow_locked',
    'order_dispatched': 'notification_order_dispatched',
    'delivery_confirmed': 'notification_delivery_confirmed',
    'delivery_recorded': 'notification_delivery_recorded',
    'wallet_credited': 'notification_wallet_credited',
    'listing_expiring': 'notification_listing_expiring',
    'price_alert': 'notification_price_alert',
}


async def send_notification(phone: str, event: str, data: dict[str, object], language: str) -> bool:
    template_key = NOTIFICATION_KEYS.get(event)
    if template_key is None:
        return False
    body = t(template_key, language, **data)
    return await whatsapp_service.send_message(to=phone, body=body)
