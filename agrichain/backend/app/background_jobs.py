from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import AsyncSessionLocal
from app.services.mandi_price import refresh_mandi_cache
from app.services.wallet_service import expire_listings, process_withdrawals


scheduler = AsyncIOScheduler()


async def expire_old_listings() -> None:
    async with AsyncSessionLocal() as session:
        await expire_listings(session)
        await session.commit()


async def refresh_mandi_prices() -> None:
    await refresh_mandi_cache()


async def process_pending_withdrawals() -> None:
    async with AsyncSessionLocal() as session:
        await process_withdrawals(session)
        await session.commit()


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(expire_old_listings, 'interval', hours=1, id='expire-listings', replace_existing=True)
    scheduler.add_job(refresh_mandi_prices, 'interval', hours=6, id='refresh-mandi-prices', replace_existing=True)
    scheduler.add_job(process_pending_withdrawals, 'interval', minutes=5, id='process-withdrawals', replace_existing=True)
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
