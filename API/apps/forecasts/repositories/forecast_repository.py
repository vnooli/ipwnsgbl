"""Repository facade: combines the Elexon HTTP client with the in-memory
cache so services never deal with HTTP or caching directly."""
from __future__ import annotations

from datetime import date

from apps.forecasts.repositories.cache import cached
from apps.forecasts.repositories.elexon_client import (
    ActualGenerationRecord,
    ElexonClient,
    ForecastRecord,
)

_client = ElexonClient()


def get_wind_actuals(start: date, end: date) -> list[ActualGenerationRecord]:
    key = f"actuals:{start.isoformat()}:{end.isoformat()}"
    return cached(key, lambda: _client.fetch_wind_actuals(start, end))


def get_wind_forecasts(start: date, end: date) -> list[ForecastRecord]:
    key = f"forecasts:{start.isoformat()}:{end.isoformat()}"
    return cached(key, lambda: _client.fetch_wind_forecasts(start, end))
