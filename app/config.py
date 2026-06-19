import os


def _build_database_url() -> str:
    if url := os.getenv("DATABASE_URL"):
        return url

    if conn_str := os.getenv("POSTGRES_CONNECTION_STRING"):
        return conn_str.replace("postgres://", "postgresql+asyncpg://", 1)

    host = os.getenv("POSTGRES_HOST", "localhost")
    user = os.getenv("POSTGRES_USERNAME", "app")
    password = os.getenv("POSTGRES_PASSWORD", "secret")
    dbname = os.getenv("POSTGRES_DATABASE_NAME", "events")
    return f"postgresql+asyncpg://{user}:{password}@{host}/{dbname}"


DATABASE_URL = _build_database_url()

EVENTS_PROVIDER_BASE_URL = os.getenv(
    "EVENTS_PROVIDER_BASE_URL",
    "http://student-system-events-provider-web.student-system-events-provider.svc:8000",
)

EVENTS_PROVIDER_API_KEY = os.getenv("EVENTS_PROVIDER_API_KEY", "")

EVENTS_PROVIDER_TIMEOUT = float(os.getenv("EVENTS_PROVIDER_TIMEOUT", "10"))

SYNC_INTERVAL_SECONDS = int(os.getenv("SYNC_INTERVAL_SECONDS", str(24 * 60 * 60)))

SYNC_INITIAL_DELAY_SECONDS = int(os.getenv("SYNC_INITIAL_DELAY_SECONDS", "5"))

SEATS_CACHE_TTL_SECONDS = int(os.getenv("SEATS_CACHE_TTL_SECONDS", "30"))

EPOCH_SYNC_DATE = "2000-01-01"

ENABLE_BACKGROUND_SYNC = os.getenv("ENABLE_BACKGROUND_SYNC", "true").lower() == "true"
