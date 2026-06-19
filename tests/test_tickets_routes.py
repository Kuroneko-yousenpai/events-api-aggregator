import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models import Event

pytestmark = pytest.mark.asyncio


async def test_create_ticket_success(client: AsyncClient, published_event: Event):
    provider_ticket_id = str(uuid.uuid4())

    with patch(
        "app.usecases.tickets.EventsProviderClient.register", new_callable=AsyncMock
    ) as mock_register:
        mock_register.return_value = provider_ticket_id

        response = await client.post(
            "/api/tickets",
            json={
                "event_id": str(published_event.id),
                "first_name": "Ivan",
                "last_name": "Ivanov",
                "email": "ivan@example.com",
                "seat": "A1",
            },
        )

        assert response.status_code == 201
        assert response.json()["ticket_id"] == provider_ticket_id
        mock_register.assert_called_once_with(
            str(published_event.id), "Ivan", "Ivanov", "ivan@example.com", "A1"
        )


async def test_create_ticket_increments_visitor_count(
    client: AsyncClient, published_event: Event, session
):
    with patch(
        "app.usecases.tickets.EventsProviderClient.register", new_callable=AsyncMock
    ) as mock_register:
        mock_register.return_value = str(uuid.uuid4())

        await client.post(
            "/api/tickets",
            json={
                "event_id": str(published_event.id),
                "first_name": "Ivan",
                "last_name": "Ivanov",
                "email": "ivan@example.com",
                "seat": "A1",
            },
        )

        await session.refresh(published_event)
        assert published_event.number_of_visitors == 1


async def test_create_ticket_event_not_found(client: AsyncClient):
    response = await client.post(
        "/api/tickets",
        json={
            "event_id": str(uuid.uuid4()),
            "first_name": "Ivan",
            "last_name": "Ivanov",
            "email": "ivan@example.com",
            "seat": "A1",
        },
    )

    assert response.status_code == 404


async def test_create_ticket_unpublished_event(client: AsyncClient, unpublished_event: Event):
    with patch(
        "app.usecases.tickets.EventsProviderClient.register", new_callable=AsyncMock
    ) as mock_register:
        response = await client.post(
            "/api/tickets",
            json={
                "event_id": str(unpublished_event.id),
                "first_name": "Ivan",
                "last_name": "Ivanov",
                "email": "ivan@example.com",
                "seat": "A1",
            },
        )

        assert response.status_code == 400
        mock_register.assert_not_called()


async def test_create_ticket_registration_closed(client: AsyncClient, expired_event: Event):
    with patch(
        "app.usecases.tickets.EventsProviderClient.register", new_callable=AsyncMock
    ) as mock_register:
        response = await client.post(
            "/api/tickets",
            json={
                "event_id": str(expired_event.id),
                "first_name": "Ivan",
                "last_name": "Ivanov",
                "email": "ivan@example.com",
                "seat": "A1",
            },
        )

        assert response.status_code == 400
        mock_register.assert_not_called()


async def test_create_ticket_seat_taken(client: AsyncClient, published_event: Event):
    from app.provider.client import SeatNotAvailableError

    with patch(
        "app.usecases.tickets.EventsProviderClient.register", new_callable=AsyncMock
    ) as mock_register:
        mock_register.side_effect = SeatNotAvailableError("A1")

        response = await client.post(
            "/api/tickets",
            json={
                "event_id": str(published_event.id),
                "first_name": "Ivan",
                "last_name": "Ivanov",
                "email": "ivan@example.com",
                "seat": "A1",
            },
        )

        assert response.status_code == 400


async def test_create_ticket_invalid_email(client: AsyncClient, published_event: Event):
    response = await client.post(
        "/api/tickets",
        json={
            "event_id": str(published_event.id),
            "first_name": "Ivan",
            "last_name": "Ivanov",
            "email": "not-an-email",
            "seat": "A1",
        },
    )

    assert response.status_code == 400


async def test_create_ticket_missing_fields(client: AsyncClient, published_event: Event):
    response = await client.post(
        "/api/tickets",
        json={"event_id": str(published_event.id), "email": "ivan@example.com"},
    )

    assert response.status_code == 400


async def test_cancel_ticket_success(client: AsyncClient, published_event: Event, session):
    from app.models import Ticket

    ticket = Ticket(
        id=uuid.uuid4(),
        event_id=published_event.id,
        first_name="Ivan",
        last_name="Ivanov",
        email="ivan@example.com",
        seat="A1",
    )
    session.add(ticket)
    await session.commit()

    with patch(
        "app.usecases.tickets.EventsProviderClient.unregister", new_callable=AsyncMock
    ) as mock_unregister:
        mock_unregister.return_value = True

        response = await client.delete(f"/api/tickets/{ticket.id}")

        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_unregister.assert_called_once_with(str(published_event.id), str(ticket.id))


async def test_cancel_ticket_not_found(client: AsyncClient):
    response = await client.delete(f"/api/tickets/{uuid.uuid4()}")

    assert response.status_code == 404
