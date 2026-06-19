from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.dependencies import get_sync_events_usecase, get_sync_state_repository
from app.repositories.sync_state import SqlAlchemySyncStateRepository
from app.schemas import SyncStatusResponse, SyncTriggerResponse
from app.usecases.sync import SyncEventsUsecase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/trigger", response_model=SyncTriggerResponse)
async def trigger_sync(
    usecase: SyncEventsUsecase = Depends(get_sync_events_usecase),
) -> SyncTriggerResponse:
    try:
        await usecase.do()
        return SyncTriggerResponse(sync_status="success")
    except Exception as exc:
        logger.exception("manual sync trigger failed")
        return SyncTriggerResponse(sync_status="failed", detail=str(exc))


@router.get("/status", response_model=SyncStatusResponse)
async def sync_status(
    sync_state: SqlAlchemySyncStateRepository = Depends(get_sync_state_repository),
) -> SyncStatusResponse:
    state = await sync_state.get()
    if state is None:
        return SyncStatusResponse(sync_status="idle")

    return SyncStatusResponse(
        sync_status=state.sync_status,
        last_sync_time=state.last_sync_time,
        last_changed_at=state.last_changed_at,
        last_error=state.last_error,
    )
