from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class EventsProviderError(Exception):
    pass


class EventNotFoundError(EventsProviderError):
    pass


class SeatNotAvailableError(EventsProviderError):
    pass


class EventNotPublishedError(EventsProviderError):
    pass


class ProviderAuthError(EventsProviderError):
    pass


class ProviderUnavailableError(EventsProviderError):
    pass


class EventsProviderClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self._api_key}

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as http_client:
            try:
                response = await http_client.request(
                    method,
                    url,
                    headers=self._headers(),
                    params=params,
                    json=json,
                )
            except httpx.TimeoutException as exc:
                raise ProviderUnavailableError(f"Provider request timed out: {url}") from exc
            except httpx.HTTPError as exc:
                raise ProviderUnavailableError(f"Provider request failed: {url}") from exc

        if response.status_code == 401:
            raise ProviderAuthError("Invalid or missing API key")
        if response.status_code == 429:
            raise ProviderUnavailableError("Rate limit exceeded")

        return response

    async def events(self, changed_at: str, cursor: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"changed_at": changed_at}
        if cursor:
            params["cursor"] = cursor

        response = await self._request("GET", f"{self._base_url}/api/events/", params=params)

        if response.status_code != 200:
            raise ProviderUnavailableError(
                f"Unexpected status {response.status_code} fetching events"
            )

        return response.json()

    async def get_events_page(self, url: str) -> dict[str, Any]:
        response = await self._request("GET", url)

        if response.status_code != 200:
            raise ProviderUnavailableError(
                f"Unexpected status {response.status_code} fetching events page"
            )

        return response.json()

    async def get_seats(self, event_id: str) -> list[str]:
        response = await self._request("GET", f"{self._base_url}/api/events/{event_id}/seats/")

        if response.status_code == 404:
            raise EventNotFoundError(event_id)

        if response.status_code == 500:
            raise EventNotPublishedError(event_id)

        if response.status_code != 200:
            raise ProviderUnavailableError(
                f"Unexpected status {response.status_code} fetching seats"
            )

        return response.json()["seats"]

    async def register(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> str:
        response = await self._request(
            "POST",
            f"{self._base_url}/api/events/{event_id}/register/",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "seat": seat,
            },
        )

        if response.status_code == 404:
            raise EventNotFoundError(event_id)

        if response.status_code == 400:
            raise SeatNotAvailableError(seat)

        if response.status_code != 201:
            raise ProviderUnavailableError(
                f"Unexpected status {response.status_code} registering for event"
            )

        return response.json()["ticket_id"]

    async def unregister(self, event_id: str, ticket_id: str) -> bool:
        response = await self._request(
            "DELETE",
            f"{self._base_url}/api/events/{event_id}/unregister/",
            json={"ticket_id": ticket_id},
        )

        if response.status_code == 404:
            raise EventNotFoundError(event_id)

        if response.status_code != 200:
            raise ProviderUnavailableError(
                f"Unexpected status {response.status_code} cancelling registration"
            )

        return response.json()["success"]
