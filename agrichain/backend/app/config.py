from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
import socket
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
APP_DIR = Path(__file__).resolve().parent
LOOPBACK_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0', '::1'}


@lru_cache(maxsize=1)
def detect_lan_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(('8.8.8.8', 80))
            candidate = probe.getsockname()[0]
            if candidate and candidate not in LOOPBACK_HOSTS:
                return candidate
    except OSError:
        pass

    try:
        candidate = socket.gethostbyname(socket.gethostname())
        if candidate and candidate not in LOOPBACK_HOSTS:
            return candidate
    except OSError:
        pass

    return None


def normalize_public_url(url: str) -> str:
    parts = urlsplit(url.rstrip('/'))
    if not parts.hostname or parts.hostname not in LOOPBACK_HOSTS:
        return url.rstrip('/')

    lan_ip = detect_lan_ip()
    if not lan_ip:
        return url.rstrip('/')

    netloc = lan_ip if parts.port is None else f'{lan_ip}:{parts.port}'
    return urlunsplit((parts.scheme or 'http', netloc, parts.path.rstrip('/'), parts.query, parts.fragment)).rstrip('/')

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / '.env',
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore',
    )

    APP_ENV: str = 'development'
    SECRET_KEY: str = 'dev-only-secret-key'
    BASE_URL: str = 'http://localhost:8000'
    FRONTEND_ORIGIN: str = 'http://localhost:5173'
    PUBLIC_VERIFY_BASE_URL: str | None = None

    DATABASE_URL: str = 'postgresql://agrichain_user:password@localhost:5432/agrichain_db'
    REDIS_URL: str = 'redis://localhost:6379/0'

    TWILIO_ACCOUNT_SID: str = ''
    TWILIO_AUTH_TOKEN: str = ''
    TWILIO_WHATSAPP_NUMBER: str = 'whatsapp:+14155238886'

    GOOGLE_API_KEY: str = ''
    AGMARKNET_API_URL: str = 'https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070'
    AGMARKNET_API_KEY: str = ''
    DEFAULT_MANDI_STATE: str = 'Karnataka'

    SESSION_TTL_SECONDS: int = 600
    MAX_WALLET_BALANCE: Decimal = Field(default=Decimal('50000.00'))
    MIN_ADD_AMOUNT: Decimal = Field(default=Decimal('10.00'))
    PLATFORM_FEE_PERCENT: Decimal = Field(default=Decimal('2.00'))
    WELCOME_BONUS_AMOUNT: Decimal = Field(default=Decimal('100.00'))
    USD_EXCHANGE_RATE: Decimal = Field(default=Decimal('84.00'))

    BLOCKCHAIN_DIFFICULTY: int = 3

    JWT_EXPIRE_MINUTES: int = 1440
    OTP_EXPIRY_SECONDS: int = 600
    OTP_MAX_ATTEMPTS: int = 3
    OTP_LOCKOUT_SECONDS: int = 900
    MESSAGE_RATE_LIMIT: int = 20
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL.startswith('postgresql://'):
            return self.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)
        if self.DATABASE_URL.startswith('sqlite:///'):
            return self.DATABASE_URL.replace('sqlite:///', 'sqlite+aiosqlite:///', 1)
        return self.DATABASE_URL

    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL.startswith('postgresql+asyncpg://'):
            return self.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://', 1)
        if self.DATABASE_URL.startswith('sqlite+aiosqlite:///'):
            return self.DATABASE_URL.replace('sqlite+aiosqlite:///', 'sqlite:///', 1)
        return self.DATABASE_URL

    @property
    def is_development(self) -> bool:
        return self.APP_ENV.lower() == 'development'

    @property
    def allowed_origins(self) -> list[str]:
        origins = {self.FRONTEND_ORIGIN.rstrip('/'), self.BASE_URL.rstrip('/')}
        if self.PUBLIC_VERIFY_BASE_URL:
            origins.add(self.PUBLIC_VERIFY_BASE_URL.rstrip('/'))
        return sorted(origin for origin in origins if origin)

    @property
    def static_dir(self) -> Path:
        return APP_DIR / 'static'

    @property
    def qr_dir(self) -> Path:
        return self.static_dir / 'qr'

    @property
    def i18n_dir(self) -> Path:
        return APP_DIR / 'i18n'

    @property
    def public_verify_url_base(self) -> str:
        preferred = self.PUBLIC_VERIFY_BASE_URL or self.FRONTEND_ORIGIN or self.BASE_URL
        return normalize_public_url(preferred)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

