from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.models import Event, EventStatus
from app.provider.client import EventNotFoundError, EventNotPublishedError, EventsProviderClient
from app.repositories.protocols import EventRepository


class EventNotFound(Exception):
    pass


class EventNotPublished(Exception):
    pass


class ListEventsUsecase:
    def __init__(self, events: EventRepository):
        self._events = events

    async def do(
        self, date_from: datetime | None, page: int, page_size: int
    ) -> tuple[list[Event], int]:
        return await self._events.list(date_from, page, page_size)


class GetEventUsecase:
    def __init__(self, events: EventRepository):
        self._events = events

    async def do(self, event_id: UUID) -> Event:
        event = await self._events.get(event_id)
        if event is None:
            raise EventNotFound(event_id)
        return event


class GetSeatsUsecase:
    def __init__(self, events: EventRepository, client: EventsProviderClient):
        self._events = events
        self._client = client

    async def do(self, event_id: UUID) -> list[str]:
        event = await self._events.get(event_id)
        if event is None:
            raise EventNotFound(event_id)

        if event.status != EventStatus.published.value:
            raise EventNotPublished(event_id)

        try:
            return await self._client.get_seats(str(event_id))
        except EventNotFoundError as exc:
            raise EventNotFound(event_id) from exc
        except EventNotPublishedError as exc:
            raise EventNotPublished(event_id) from exc
