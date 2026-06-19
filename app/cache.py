import time
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._store.get(key)
        if entry is None:
            return None

        expires_at, value = entry
        if time.monotonic() >= expires_at:
            self._store.pop(key, None)
            return None

        return value

    def set(self, key: str, value: T) -> None:
        self._store[key] = (time.monotonic() + self._ttl, value)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)
