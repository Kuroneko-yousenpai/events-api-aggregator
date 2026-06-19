import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://app:secret@localhost:5432/events",
)

EVENTS_PROVIDER_BASE_URL = os.getenv(
    "EVENTS_PROVIDER_BASE_URL",
    "https://events-provider.dev-2.python-labs.ru",
)

EVENTS_PROVIDER_API_KEY = os.getenv("EVENTS_PROVIDER_API_KEY", "")

EVENTS_PROVIDER_TIMEOUT = float(os.getenv("EVENTS_PROVIDER_TIMEOUT", "10"))

SYNC_INTERVAL_SECONDS = int(os.getenv("SYNC_INTERVAL_SECONDS", str(24 * 60 * 60)))

SYNC_INITIAL_DELAY_SECONDS = int(os.getenv("SYNC_INITIAL_DELAY_SECONDS", "5"))

SEATS_CACHE_TTL_SECONDS = int(os.getenv("SEATS_CACHE_TTL_SECONDS", "30"))

EPOCH_SYNC_DATE = "2000-01-01"

ENABLE_BACKGROUND_SYNC = os.getenv("ENABLE_BACKGROUND_SYNC", "true").lower() == "true"
