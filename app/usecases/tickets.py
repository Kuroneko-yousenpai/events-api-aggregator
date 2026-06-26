from __future__ import annotations

import datetime as dt
from uuid import UUID

from app.models import EventStatus
from app.provider.client import (
    EventNotFoundError,
    EventsProviderClient,
    SeatNotAvailableError,
)
from app.repositories.protocols import EventRepository, TicketRepository


class EventNotFound(Exception):
    pass


class EventNotPublished(Exception):
    pass


class RegistrationClosed(Exception):
    pass


class SeatNotAvailable(Exception):
    pass


class TicketNotFound(Exception):
    pass


class CreateTicketUsecase:
    def __init__(
        self,
        client: EventsProviderClient,
        events: EventRepository,
        tickets: TicketRepository,
    ):
        self._client = client
        self._events = events
        self._tickets = tickets

    async def do(
        self,
        event_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ):
        event = await self._events.get(event_id)
        if event is None:
            raise EventNotFound(event_id)

        if event.status != EventStatus.published:
            raise EventNotPublished(event_id)

        if event.registration_deadline < dt.datetime.now(dt.UTC):
            raise RegistrationClosed(event_id)

        try:
            ticket_id = await self._client.register(
                str(event_id), first_name, last_name, email, seat
            )
        except EventNotFoundError as exc:
            raise EventNotFound(event_id) from exc
        except SeatNotAvailableError as exc:
            raise SeatNotAvailable(seat) from exc

        ticket = await self._tickets.create(
            UUID(ticket_id), event_id, first_name, last_name, email, seat
        )
        await self._events.increment_visitors(event_id, +1)

        return ticket


class CancelTicketUsecase:
    def __init__(
        self,
        client: EventsProviderClient,
        events: EventRepository,
        tickets: TicketRepository,
    ):
        self._client = client
        self._events = events
        self._tickets = tickets

    async def do(self, ticket_id: UUID) -> None:
        ticket = await self._tickets.get(ticket_id)
        if ticket is None:
            raise TicketNotFound(ticket_id)

        try:
            await self._client.unregister(str(ticket.event_id), str(ticket_id))
        except EventNotFoundError as exc:
            raise EventNotFound(ticket.event_id) from exc

        await self._tickets.mark_cancelled(ticket_id)
        await self._events.increment_visitors(ticket.event_id, -1)
