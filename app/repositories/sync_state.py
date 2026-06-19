from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SyncState, SyncStatus

_SINGLETON_ID = 1


class SqlAlchemySyncStateRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self) -> SyncState | None:
        return await self._session.get(SyncState, _SINGLETON_ID)

    async def _upsert(self, **fields) -> None:
        stmt = (
            pg_insert(SyncState)
            .values(id=_SINGLETON_ID, **fields)
            .on_conflict_do_update(index_elements=[SyncState.id], set_=fields)
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def mark_running(self) -> None:
        await self._upsert(sync_status=SyncStatus.running.value, last_error=None)

    async def mark_success(self, last_changed_at: datetime | None) -> None:
        fields = {
            "sync_status": SyncStatus.success.value,
            "last_sync_time": datetime.now(UTC),
            "last_error": None,
        }
        if last_changed_at is not None:
            fields["last_changed_at"] = last_changed_at
        await self._upsert(**fields)

    async def mark_failed(self, error: str) -> None:
        await self._upsert(
            sync_status=SyncStatus.failed.value,
            last_sync_time=datetime.now(UTC),
            last_error=error[:2000],
        )
