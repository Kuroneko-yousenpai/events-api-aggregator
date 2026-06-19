from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models import Event, Place, SyncState
from app.repositories.events import SqlAlchemyEventRepository, SqlAlchemyPlaceRepository
from app.repositories.sync_state import SqlAlchemySyncStateRepository
from app.usecases.sync import SyncEventsUsecase

pytestmark = pytest.mark.asyncio


def _raw_event(event_id=None, place_id=None, changed_at="2026-01-04T22:28:35.325270+03:00"):
    return {
        "id": event_id or str(uuid4()),
        "name": "Python Conference",
        "place": {
            "id": place_id or str(uuid4()),
            "name": "Tech Park Hall",
            "city": "Moscow",
            "address": "Lenina st, 1",
            "seats_pattern": "A1-1000,B1-2000",
            "changed_at": "2025-01-01T03:00:00+03:00",
            "created_at": "2025-01-01T03:00:00+03:00",
        },
        "event_time": "2026-01-11T17:00:00+03:00",
        "registration_deadline": "2026-01-10T17:00:00+03:00",
        "status": "published",
        "number_of_visitors": 5,
        "changed_at": changed_at,
        "created_at": "2026-01-04T22:28:35.325302+03:00",
        "status_changed_at": "2026-01-04T22:28:35.325386+03:00",
    }


async def test_sync_first_run_uses_epoch_date(session):
    mock_client = AsyncMock()
    mock_client.events.return_value = {"next": None, "previous": None, "results": []}

    usecase = SyncEventsUsecase(
        client=mock_client,
        places=SqlAlchemyPlaceRepository(session),
        events=SqlAlchemyEventRepository(session),
        sync_state=SqlAlchemySyncStateRepository(session),
    )

    await usecase.do()

    mock_client.events.assert_called_once_with("2000-01-01")


async def test_sync_persists_events_and_places(session):
    raw = _raw_event()
    mock_client = AsyncMock()
    mock_client.events.return_value = {
        "next": None,
        "previous": None,
        "results": [raw],
    }

    usecase = SyncEventsUsecase(
        client=mock_client,
        places=SqlAlchemyPlaceRepository(session),
        events=SqlAlchemyEventRepository(session),
        sync_state=SqlAlchemySyncStateRepository(session),
    )

    result = await usecase.do()
    await session.commit()

    assert result["synced_count"] == 1

    saved_event = (await session.execute(select(Event).where(Event.id == raw["id"]))).scalar_one()
    assert saved_event.name == "Python Conference"

    saved_place = (
        await session.execute(select(Place).where(Place.id == raw["place"]["id"]))
    ).scalar_one()
    assert saved_place.city == "Moscow"


async def test_sync_upserts_existing_event(session):
    raw = _raw_event()
    mock_client = AsyncMock()
    mock_client.events.return_value = {
        "next": None,
        "previous": None,
        "results": [raw],
    }

    usecase = SyncEventsUsecase(
        client=mock_client,
        places=SqlAlchemyPlaceRepository(session),
        events=SqlAlchemyEventRepository(session),
        sync_state=SqlAlchemySyncStateRepository(session),
    )

    await usecase.do()
    await session.commit()

    updated_raw = dict(raw, name="Python Conference (Updated)")
    mock_client.events.return_value = {
        "next": None,
        "previous": None,
        "results": [updated_raw],
    }

    await usecase.do()
    await session.commit()

    count = (await session.execute(select(Event).where(Event.id == raw["id"]))).scalars().all()
    assert len(count) == 1
    assert count[0].name == "Python Conference (Updated)"


async def test_sync_updates_sync_state_on_success(session):
    raw = _raw_event(changed_at="2026-01-04T22:28:35.325270+03:00")
    mock_client = AsyncMock()
    mock_client.events.return_value = {
        "next": None,
        "previous": None,
        "results": [raw],
    }

    usecase = SyncEventsUsecase(
        client=mock_client,
        places=SqlAlchemyPlaceRepository(session),
        events=SqlAlchemyEventRepository(session),
        sync_state=SqlAlchemySyncStateRepository(session),
    )

    await usecase.do()
    await session.commit()

    state = (await session.execute(select(SyncState))).scalar_one()
    assert state.sync_status == "success"
    assert state.last_changed_at is not None


async def test_sync_second_run_uses_last_changed_at(session):
    raw = _raw_event(changed_at="2026-01-04T22:28:35.325270+03:00")
    mock_client = AsyncMock()
    mock_client.events.return_value = {
        "next": None,
        "previous": None,
        "results": [raw],
    }

    usecase = SyncEventsUsecase(
        client=mock_client,
        places=SqlAlchemyPlaceRepository(session),
        events=SqlAlchemyEventRepository(session),
        sync_state=SqlAlchemySyncStateRepository(session),
    )

    await usecase.do()
    await session.commit()

    mock_client.events.return_value = {"next": None, "previous": None, "results": []}
    await usecase.do()

    second_call_args = mock_client.events.call_args_list[1]
    assert second_call_args.args[0] == "2026-01-04"


async def test_sync_marks_failed_on_error(session):
    mock_client = AsyncMock()
    mock_client.events.side_effect = RuntimeError("provider down")

    usecase = SyncEventsUsecase(
        client=mock_client,
        places=SqlAlchemyPlaceRepository(session),
        events=SqlAlchemyEventRepository(session),
        sync_state=SqlAlchemySyncStateRepository(session),
    )

    with pytest.raises(RuntimeError):
        await usecase.do()

    state = (await session.execute(select(SyncState))).scalar_one()
    assert state.sync_status == "failed"
    assert "provider down" in state.last_error


async def test_manual_sync_trigger_endpoint(client: AsyncClient):
    with patch("app.usecases.sync.SyncEventsUsecase.do", new_callable=AsyncMock) as mock_do:
        mock_do.return_value = {"synced_count": 0, "max_changed_at": None}

        response = await client.post("/api/sync/trigger")

        assert response.status_code == 200
        assert response.json()["sync_status"] == "success"
        mock_do.assert_called_once()


async def test_manual_sync_trigger_handles_failure(client: AsyncClient):
    with patch("app.usecases.sync.SyncEventsUsecase.do", new_callable=AsyncMock) as mock_do:
        mock_do.side_effect = RuntimeError("boom")

        response = await client.post("/api/sync/trigger")

        assert response.status_code == 200
        assert response.json()["sync_status"] == "failed"
