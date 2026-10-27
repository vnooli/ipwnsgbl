"""Minimal in-memory TTL cache in front of the Elexon client.

Trade-off (documented in README): a full database was judged unnecessary for
this assignment's scope (a single month of 30-minute data, read-heavy,
re-derivable from Elexon at any time). An in-memory cache avoids
infrastructure while still sparing the upstream API from a fresh call on
every page load. Trade-off: the cache is per-process and lost on restart, and
does not retain full publish-time history beyond what Elexon itself still
serves - if Elexon's retention window ever drops data, a long-lived DB would
be the next step, not this cache.
"""
from __future__ import annotations

import threading
import time
from datetime import date
from typing import Callable, TypeVar

from django.conf import settings

T = TypeVar("T")

_lock = threading.Lock()
_store: dict[str, tuple[float, object]] = {}
_last_refresh: dict[str, str] = {}


def cached(key: str, loader: Callable[[], T]) -> T:
    ttl = settings.ELEXON_CACHE_TTL_SECONDS
    now = time.time()
    with _lock:
        entry = _store.get(key)
        if entry is not None and (now - entry[0]) < ttl:
            return entry[1]  # type: ignore[return-value]

    value = loader()
    with _lock:
        _store[key] = (now, value)
        _last_refresh[key] = date.fromtimestamp(now).isoformat()
    return value


def invalidate(prefix: str | None = None) -> int:
    with _lock:
        if prefix is None:
            count = len(_store)
            _store.clear()
            return count
        keys = [k for k in _store if k.startswith(prefix)]
        for k in keys:
            _store.pop(k, None)
        return len(keys)


def status() -> dict:
    with _lock:
        return {
            "cached_keys": sorted(_store.keys()),
            "cache_ttl_seconds": settings.ELEXON_CACHE_TTL_SECONDS,
        }
