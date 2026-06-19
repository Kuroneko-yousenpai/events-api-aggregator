from datetime import timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models import Event, Place

pytestmark = pytest.mark.asyncio


async def test_list_events_empty(client: AsyncClient):
    response = await client.get("/api/events")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 0
    assert body["results"] == []
    assert body["next"] is None
    assert body["previous"] is None


async def test_list_events_returns_results(client: AsyncClient, published_event: Event):
    response = await client.get("/api/events")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["results"][0]["id"] == str(published_event.id)
    assert body["results"][0]["place"]["city"] == "Moscow"


async def test_list_events_date_filter_excludes_past(
    client: AsyncClient, published_event: Event, expired_event: Event
):
    from datetime import date, timedelta

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    response = await client.get("/api/events", params={"date_from": tomorrow})

    assert response.status_code == 200
    body = response.json()
    ids = [r["id"] for r in body["results"]]
    assert str(published_event.id) in ids
    assert str(expired_event.id) not in ids


async def test_list_events_pagination(client: AsyncClient, session, place: Place):
    import uuid
    from datetime import datetime, timedelta

    now = datetime.now(timezone.utc)
    for i in range(5):
        e = Event(
            id=uuid.uuid4(),
            name=f"Event {i}",
            place_id=place.id,
            event_time=now + timedelta(days=i + 1),
            registration_deadline=now + timedelta(days=i),
            status="published",
            number_of_visitors=0,
            changed_at=now,
            created_at=now,
            status_changed_at=now,
        )
        session.add(e)
    await session.commit()

    response = await client.get("/api/events", params={"page": 1, "page_size": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 5
    assert len(body["results"]) == 2
    assert body["next"] is not None
    assert body["previous"] is None


async def test_get_event_detail(client: AsyncClient, published_event: Event):
    response = await client.get(f"/api/events/{published_event.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(published_event.id)
    assert body["place"]["seats_pattern"] == "A1-10,B1-10"


async def test_get_event_detail_not_found(client: AsyncClient):
    import uuid

    response = await client.get(f"/api/events/{uuid.uuid4()}")

    assert response.status_code == 404


async def test_get_seats_success(client: AsyncClient, published_event: Event):
    with patch(
        "app.usecases.events.EventsProviderClient.get_seats", new_callable=AsyncMock
    ) as mock_get_seats:
        mock_get_seats.return_value = ["A1", "A2", "B5"]

        response = await client.get(f"/api/events/{published_event.id}/seats")

        assert response.status_code == 200
        body = response.json()
        assert body["available_seats"] == ["A1", "A2", "B5"]
        assert body["event_id"] == str(published_event.id)


async def test_get_seats_uses_cache_on_second_call(client: AsyncClient, published_event: Event):
    with patch(
        "app.usecases.events.EventsProviderClient.get_seats", new_callable=AsyncMock
    ) as mock_get_seats:
        mock_get_seats.return_value = ["A1"]

        first = await client.get(f"/api/events/{published_event.id}/seats")
        second = await client.get(f"/api/events/{published_event.id}/seats")

        assert first.status_code == 200
        assert second.status_code == 200
        mock_get_seats.assert_called_once()


async def test_get_seats_unpublished_event_returns_400_not_500(
    client: AsyncClient, unpublished_event: Event
):
    with patch(
        "app.usecases.events.EventsProviderClient.get_seats", new_callable=AsyncMock
    ) as mock_get_seats:
        response = await client.get(f"/api/events/{unpublished_event.id}/seats")

        assert response.status_code == 400
        mock_get_seats.assert_not_called()


async def test_get_seats_event_not_found(client: AsyncClient):
    import uuid

    response = await client.get(f"/api/events/{uuid.uuid4()}/seats")

    assert response.status_code == 404


async def test_health_check(client: AsyncClient):
    response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
