from unittest.mock import AsyncMock

import pytest

from app.provider.client import EventsProviderClient
from app.provider.paginator import EventsPaginator

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_client():
    return AsyncMock(spec=EventsProviderClient)


async def test_single_page(mock_client):
    mock_client.events.return_value = {
        "next": None,
        "previous": None,
        "results": [{"id": "1"}, {"id": "2"}],
    }

    events = [e async for e in EventsPaginator(mock_client, "2000-01-01")]

    assert events == [{"id": "1"}, {"id": "2"}]
    mock_client.events.assert_called_once_with("2000-01-01")
    mock_client.get_events_page.assert_not_called()


async def test_multiple_pages(mock_client):
    mock_client.events.return_value = {
        "next": "http://provider/api/events/?cursor=abc",
        "previous": None,
        "results": [{"id": "1"}],
    }
    mock_client.get_events_page.side_effect = [
        {
            "next": "http://provider/api/events/?cursor=def",
            "previous": "...",
            "results": [{"id": "2"}],
        },
        {
            "next": None,
            "previous": "...",
            "results": [{"id": "3"}],
        },
    ]

    events = [e async for e in EventsPaginator(mock_client, "2000-01-01")]

    assert events == [{"id": "1"}, {"id": "2"}, {"id": "3"}]
    mock_client.events.assert_called_once_with("2000-01-01")
    assert mock_client.get_events_page.call_count == 2
    mock_client.get_events_page.assert_any_call("http://provider/api/events/?cursor=abc")
    mock_client.get_events_page.assert_any_call("http://provider/api/events/?cursor=def")


async def test_empty_first_page(mock_client):
    mock_client.events.return_value = {"next": None, "previous": None, "results": []}

    events = [e async for e in EventsPaginator(mock_client, "2000-01-01")]

    assert events == []


async def test_paginator_is_reusable_iterator_protocol(mock_client):
    mock_client.events.return_value = {
        "next": None,
        "previous": None,
        "results": [{"id": "1"}],
    }

    paginator = EventsPaginator(mock_client, "2000-01-01")
    assert paginator.__aiter__() is paginator

    collected = []
    async for event in paginator:
        collected.append(event)

    assert collected == [{"id": "1"}]


async def test_stop_iteration_after_exhausted(mock_client):
    mock_client.events.return_value = {"next": None, "previous": None, "results": []}

    paginator = EventsPaginator(mock_client, "2000-01-01")

    with pytest.raises(StopAsyncIteration):
        await paginator.__anext__()

    # Calling again should still raise, not re-fetch.
    with pytest.raises(StopAsyncIteration):
        await paginator.__anext__()

    mock_client.events.assert_called_once()
