import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.responses import JSONResponse

from app.config import (
    ENABLE_BACKGROUND_SYNC,
    SYNC_INITIAL_DELAY_SECONDS,
    SYNC_INTERVAL_SECONDS,
)
from app.database import async_session
from app.dependencies import get_provider_client
from app.repositories.events import SqlAlchemyEventRepository, SqlAlchemyPlaceRepository
from app.repositories.sync_state import SqlAlchemySyncStateRepository
from app.routes.events import router as events_router
from app.routes.health import router as health_router
from app.routes.sync import router as sync_router
from app.routes.tickets import router as tickets_router
from app.usecases.sync import SyncEventsUsecase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)


async def _run_sync_once() -> None:
    async with async_session() as session:
        usecase = SyncEventsUsecase(
            client=get_provider_client(),
            places=SqlAlchemyPlaceRepository(session),
            events=SqlAlchemyEventRepository(session),
            sync_state=SqlAlchemySyncStateRepository(session),
        )
        try:
            await usecase.do()
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _background_sync_loop() -> None:
    await asyncio.sleep(SYNC_INITIAL_DELAY_SECONDS)

    while True:
        try:
            await _run_sync_once()
        except Exception:
            logger.exception("background sync iteration failed")

        await asyncio.sleep(SYNC_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if ENABLE_BACKGROUND_SYNC:
        task = asyncio.create_task(_background_sync_loop())

    yield

    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Events Aggregator", lifespan=lifespan)
app.include_router(health_router)
app.include_router(sync_router)
app.include_router(events_router)
app.include_router(tickets_router)


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request, exc):
    return JSONResponse(status_code=500, content={"detail": str(exc)})
