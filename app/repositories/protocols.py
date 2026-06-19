from __future__ import annotations

import typing
from datetime import datetime
from uuid import UUID

if typing.TYPE_CHECKING:
    from app.models import Event, Place, SyncState, Ticket


class PlaceRepository(typing.Protocol):
    async def upsert(self, place_data: dict) -> Place: ...


class EventRepository(typing.Protocol):
    async def upsert(self, event_data: dict, place_id: UUID) -> Event: ...

    async def get(self, event_id: UUID) -> Event | None: ...

    async def list(
        self,
        date_from: datetime | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Event], int]: ...

    async def increment_visitors(self, event_id: UUID, delta: int) -> None: ...


class TicketRepository(typing.Protocol):
    async def create(
        self,
        ticket_id: UUID,
        event_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> Ticket: ...

    async def get(self, ticket_id: UUID) -> Ticket | None: ...

    async def mark_cancelled(self, ticket_id: UUID) -> None: ...


class SyncStateRepository(typing.Protocol):
    async def get(self) -> SyncState | None: ...

    async def mark_running(self) -> None: ...

    async def mark_success(self, last_changed_at: datetime | None) -> None: ...

    async def mark_failed(self, error: str) -> None: ...
