from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import (
    EVENTS_PROVIDER_API_KEY,
    EVENTS_PROVIDER_BASE_URL,
    EVENTS_PROVIDER_TIMEOUT,
)
from app.database import get_session
from app.provider.client import EventsProviderClient
from app.repositories.events import SqlAlchemyEventRepository, SqlAlchemyPlaceRepository
from app.repositories.sync_state import SqlAlchemySyncStateRepository
from app.repositories.tickets import SqlAlchemyTicketRepository
from app.usecases.events import GetEventUsecase, GetSeatsUsecase, ListEventsUsecase
from app.usecases.sync import SyncEventsUsecase
from app.usecases.tickets import CancelTicketUsecase, CreateTicketUsecase


def get_provider_client() -> EventsProviderClient:
    return EventsProviderClient(
        base_url=EVENTS_PROVIDER_BASE_URL,
        api_key=EVENTS_PROVIDER_API_KEY,
        timeout=EVENTS_PROVIDER_TIMEOUT,
    )


async def get_event_repository(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[SqlAlchemyEventRepository, None]:
    yield SqlAlchemyEventRepository(session)


async def get_place_repository(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[SqlAlchemyPlaceRepository, None]:
    yield SqlAlchemyPlaceRepository(session)


async def get_ticket_repository(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[SqlAlchemyTicketRepository, None]:
    yield SqlAlchemyTicketRepository(session)


async def get_sync_state_repository(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[SqlAlchemySyncStateRepository, None]:
    yield SqlAlchemySyncStateRepository(session)


def get_list_events_usecase(
    events: SqlAlchemyEventRepository = Depends(get_event_repository),
) -> ListEventsUsecase:
    return ListEventsUsecase(events)


def get_get_event_usecase(
    events: SqlAlchemyEventRepository = Depends(get_event_repository),
) -> GetEventUsecase:
    return GetEventUsecase(events)


def get_get_seats_usecase(
    events: SqlAlchemyEventRepository = Depends(get_event_repository),
    client: EventsProviderClient = Depends(get_provider_client),
) -> GetSeatsUsecase:
    return GetSeatsUsecase(events, client)


def get_create_ticket_usecase(
    events: SqlAlchemyEventRepository = Depends(get_event_repository),
    tickets: SqlAlchemyTicketRepository = Depends(get_ticket_repository),
    client: EventsProviderClient = Depends(get_provider_client),
) -> CreateTicketUsecase:
    return CreateTicketUsecase(client, events, tickets)


def get_cancel_ticket_usecase(
    events: SqlAlchemyEventRepository = Depends(get_event_repository),
    tickets: SqlAlchemyTicketRepository = Depends(get_ticket_repository),
    client: EventsProviderClient = Depends(get_provider_client),
) -> CancelTicketUsecase:
    return CancelTicketUsecase(client, events, tickets)


def get_sync_events_usecase(
    places: SqlAlchemyPlaceRepository = Depends(get_place_repository),
    events: SqlAlchemyEventRepository = Depends(get_event_repository),
    sync_state: SqlAlchemySyncStateRepository = Depends(get_sync_state_repository),
    client: EventsProviderClient = Depends(get_provider_client),
) -> SyncEventsUsecase:
    return SyncEventsUsecase(client, places, events, sync_state)
