from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import AsyncSessionLocal
from app.services.mandi_price import FALLBACK_PRICES, get_mandi_price
from app.services.wallet_service import expire_listings as expire_listings_service
from app.services.wallet_service import process_withdrawals as process_withdrawals_service


scheduler = AsyncIOScheduler()


async def expire_listings() -> None:
    async with AsyncSessionLocal() as session:
        await expire_listings_service(session)
        await session.commit()


async def refresh_mandi_prices() -> None:
    for crop in FALLBACK_PRICES:
        await get_mandi_price(crop)


async def process_withdrawals() -> None:
    async with AsyncSessionLocal() as session:
        await process_withdrawals_service(session)
        await session.commit()


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(expire_listings, 'interval', hours=1, id='expire-listings', replace_existing=True)
    scheduler.add_job(refresh_mandi_prices, 'interval', hours=6, id='refresh-mandi-prices', replace_existing=True)
    scheduler.add_job(process_withdrawals, 'interval', minutes=5, id='process-withdrawals', replace_existing=True)
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


__all__ = ['expire_listings', 'refresh_mandi_prices', 'process_withdrawals', 'start_scheduler', 'stop_scheduler']
