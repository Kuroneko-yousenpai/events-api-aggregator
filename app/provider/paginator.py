from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.provider.client import EventsProviderClient


class EventsPaginator:
    def __init__(self, client: EventsProviderClient, changed_at: str):
        self._client = client
        self._changed_at = changed_at
        self._buffer: list[dict[str, Any]] = []
        self._next_url: str | None = None
        self._started = False
        self._exhausted = False

    def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self._buffer:
            return self._buffer.pop(0)

        if self._exhausted:
            raise StopAsyncIteration

        await self._fetch_next_page()

        if self._buffer:
            return self._buffer.pop(0)

        raise StopAsyncIteration

    async def _fetch_next_page(self) -> None:
        if not self._started:
            page = await self._client.events(self._changed_at)
            self._started = True
        else:
            if self._next_url is None:
                self._exhausted = True
                return
            page = await self._client.get_events_page(self._next_url)

        self._buffer = list(page.get("results", []))
        self._next_url = page.get("next")

        if self._next_url is None:
            self._exhausted = True
