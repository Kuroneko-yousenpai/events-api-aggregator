from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.provider.client import (
    EventNotFoundError,
    EventNotPublishedError,
    EventsProviderClient,
    ProviderAuthError,
    ProviderUnavailableError,
    SeatNotAvailableError,
)

pytestmark = pytest.mark.asyncio


def make_response(status_code: int, json_data=None):
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_data or {}
    return response


@pytest.fixture
def mock_http_client():
    with patch("httpx.AsyncClient") as mock_cls:
        instance = MagicMock()
        instance.request = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = instance
        yield instance


@pytest.fixture
def client():
    return EventsProviderClient(base_url="https://events-provider.test", api_key="secret-key")


async def test_events_success(client, mock_http_client):
    page = {"next": None, "previous": None, "results": [{"id": "1"}]}
    mock_http_client.request.return_value = make_response(200, page)

    result = await client.events("2000-01-01")

    assert result == page
    mock_http_client.request.assert_called_once()
    _, kwargs = mock_http_client.request.call_args
    assert kwargs["params"] == {"changed_at": "2000-01-01"}
    assert kwargs["headers"]["x-api-key"] == "secret-key"


async def test_events_with_cursor(client, mock_http_client):
    mock_http_client.request.return_value = make_response(
        200, {"next": None, "previous": None, "results": []}
    )

    await client.events("2000-01-01", cursor="abc123")

    _, kwargs = mock_http_client.request.call_args
    assert kwargs["params"] == {"changed_at": "2000-01-01", "cursor": "abc123"}


async def test_events_unauthorized(client, mock_http_client):
    mock_http_client.request.return_value = make_response(401, {"detail": "no key"})

    with pytest.raises(ProviderAuthError):
        await client.events("2000-01-01")


async def test_events_rate_limited(client, mock_http_client):
    mock_http_client.request.return_value = make_response(429)

    with pytest.raises(ProviderUnavailableError):
        await client.events("2000-01-01")


async def test_events_unexpected_status(client, mock_http_client):
    mock_http_client.request.return_value = make_response(500)

    with pytest.raises(ProviderUnavailableError):
        await client.events("2000-01-01")


async def test_get_seats_success(client, mock_http_client):
    mock_http_client.request.return_value = make_response(200, {"seats": ["A1", "A2", "B1"]})

    seats = await client.get_seats("event-1")

    assert seats == ["A1", "A2", "B1"]


async def test_get_seats_event_not_found(client, mock_http_client):
    mock_http_client.request.return_value = make_response(404, {"detail": "not found"})

    with pytest.raises(EventNotFoundError):
        await client.get_seats("missing-event")


async def test_get_seats_event_not_published(client, mock_http_client):
    mock_http_client.request.return_value = make_response(500)

    with pytest.raises(EventNotPublishedError):
        await client.get_seats("draft-event")


async def test_register_success(client, mock_http_client):
    mock_http_client.request.return_value = make_response(201, {"ticket_id": "ticket-123"})

    ticket_id = await client.register("event-1", "Ivan", "Ivanov", "ivan@example.com", "A1")

    assert ticket_id == "ticket-123"
    _, kwargs = mock_http_client.request.call_args
    assert kwargs["json"] == {
        "first_name": "Ivan",
        "last_name": "Ivanov",
        "email": "ivan@example.com",
        "seat": "A1",
    }


async def test_register_seat_taken(client, mock_http_client):
    mock_http_client.request.return_value = make_response(
        400, ["This ticket is not available (already sold)."]
    )

    with pytest.raises(SeatNotAvailableError):
        await client.register("event-1", "Ivan", "Ivanov", "ivan@example.com", "A1")


async def test_register_event_not_found(client, mock_http_client):
    mock_http_client.request.return_value = make_response(404, {"detail": "not found"})

    with pytest.raises(EventNotFoundError):
        await client.register("missing", "Ivan", "Ivanov", "ivan@example.com", "A1")


async def test_unregister_success(client, mock_http_client):
    mock_http_client.request.return_value = make_response(200, {"success": True})

    result = await client.unregister("event-1", "ticket-123")

    assert result is True
    _, kwargs = mock_http_client.request.call_args
    assert kwargs["json"] == {"ticket_id": "ticket-123"}


async def test_unregister_event_not_found(client, mock_http_client):
    mock_http_client.request.return_value = make_response(404, {"detail": "not found"})

    with pytest.raises(EventNotFoundError):
        await client.unregister("missing", "ticket-123")


async def test_timeout_raises_provider_unavailable(client, mock_http_client):
    mock_http_client.request.side_effect = httpx.TimeoutException("timed out")

    with pytest.raises(ProviderUnavailableError):
        await client.events("2000-01-01")


async def test_network_error_raises_provider_unavailable(client, mock_http_client):
    mock_http_client.request.side_effect = httpx.ConnectError("connection refused")

    with pytest.raises(ProviderUnavailableError):
        await client.events("2000-01-01")
