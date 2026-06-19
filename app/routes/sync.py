from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.dependencies import get_sync_events_usecase
from app.schemas import SyncTriggerResponse
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
    except Exception:
        logger.exception("manual sync trigger failed")
        return SyncTriggerResponse(sync_status="failed")
