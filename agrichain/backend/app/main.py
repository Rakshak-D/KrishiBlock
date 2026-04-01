from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import AsyncSessionLocal, close_db, init_db
from app.models.listing import Listing
from app.routers import auth, dashboard, ledger, listings, orders, verify, wallet, webhook
from app.services.qr_service import generate_listing_qr
from app.services.scheduler import start_scheduler, stop_scheduler
from app.utils.serializers import envelope


logger = logging.getLogger(__name__)
settings = get_settings()
settings.static_dir.mkdir(parents=True, exist_ok=True)
settings.qr_dir.mkdir(parents=True, exist_ok=True)


async def refresh_verify_qr_assets() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Listing).options(selectinload(Listing.farmer)))
        changed = False
        for listing in result.scalars().unique().all():
            listing.qr_code_path = generate_listing_qr(listing, listing.farmer)
            changed = True
        if changed:
            await session.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    await refresh_verify_qr_assets()
    start_scheduler()
    yield
    stop_scheduler()
    await close_db()


app = FastAPI(title='AgriChain API', version='1.0.0', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.mount('/static', StaticFiles(directory=settings.static_dir), name='static')


@app.middleware('http')
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; "
        "connect-src 'self' http: https:; "
        "font-src 'self' data:; "
        "frame-ancestors 'none'; "
        "base-uri 'self';"
    )
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=envelope(None, str(exc.detail), success=False))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception('Unhandled exception for %s %s: %s', request.method, request.url.path, exc)
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=envelope(None, 'Something went wrong. Please try again.', success=False))


app.include_router(webhook.router)
app.include_router(auth.router)
app.include_router(listings.router)
app.include_router(verify.router)
app.include_router(dashboard.router)
app.include_router(wallet.router)
app.include_router(orders.router)

