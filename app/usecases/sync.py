from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from app.config import EPOCH_SYNC_DATE
from app.provider.client import EventsProviderClient
from app.provider.paginator import EventsPaginator
from app.repositories.protocols import EventRepository, PlaceRepository, SyncStateRepository

logger = logging.getLogger(__name__)


class SyncEventsUsecase:
    def __init__(
        self,
        client: EventsProviderClient,
        places: PlaceRepository,
        events: EventRepository,
        sync_state: SyncStateRepository,
    ):
        self._client = client
        self._places = places
        self._events = events
        self._sync_state = sync_state

    async def do(self) -> dict:
        state = await self._sync_state.get()
        if state is not None and state.last_changed_at is not None:
            changed_at = state.last_changed_at.date().isoformat()
        else:
            changed_at = EPOCH_SYNC_DATE

        await self._sync_state.mark_running()
        logger.info("sync started changed_at=%s", changed_at)

        max_changed_at: datetime | None = None
        synced_count = 0

        try:
            async for raw_event in EventsPaginator(self._client, changed_at):
                place_data = raw_event["place"]
                place = await self._places.upsert(
                    {
                        "id": UUID(place_data["id"]),
                        "name": place_data["name"],
                        "city": place_data["city"],
                        "address": place_data["address"],
                        "seats_pattern": place_data["seats_pattern"],
                        "changed_at": _parse_dt(place_data["changed_at"]),
                        "created_at": _parse_dt(place_data["created_at"]),
                    }
                )

                event_changed_at = _parse_dt(raw_event["changed_at"])
                await self._events.upsert(
                    {
                        "id": UUID(raw_event["id"]),
                        "name": raw_event["name"],
                        "event_time": _parse_dt(raw_event["event_time"]),
                        "registration_deadline": _parse_dt(raw_event["registration_deadline"]),
                        "status": raw_event["status"],
                        "number_of_visitors": raw_event["number_of_visitors"],
                        "changed_at": event_changed_at,
                        "created_at": _parse_dt(raw_event["created_at"]),
                        "status_changed_at": _parse_dt(raw_event["status_changed_at"]),
                    },
                    place_id=place.id,
                )

                synced_count += 1
                if max_changed_at is None or event_changed_at > max_changed_at:
                    max_changed_at = event_changed_at

        except Exception as exc:
            logger.exception("sync failed")
            await self._sync_state.mark_failed(str(exc))
            raise

        await self._sync_state.mark_success(max_changed_at)
        logger.info("sync finished synced_count=%s", synced_count)

        return {"synced_count": synced_count, "max_changed_at": max_changed_at}


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
