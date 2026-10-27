"""HTTP client for the Elexon Insights (BMRS) API.

Scope is intentionally narrow: only the two datasets the assignment allows -
FUELHH (actual fuel-type generation) and WINDFOR (wind forecast). All HTTP
concerns (timeouts, retries, pagination, response parsing) live here so the
rest of the app never talks to `requests` directly.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import requests
from django.conf import settings

from apps.forecasts.exceptions import UpstreamDataError

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_SECONDS = 15
_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = 1.5


@dataclass(frozen=True)
class ActualGenerationRecord:
    start_time: str  # ISO-8601, as returned by Elexon (UTC)
    settlement_period: int | None
    generation_mw: float
    fuel_type: str


@dataclass(frozen=True)
class ForecastRecord:
    start_time: str  # ISO-8601, as returned by Elexon (UTC)
    publish_time: str  # ISO-8601, as returned by Elexon (UTC)
    generation_mw: float


class ElexonClient:
    """Thin, retrying HTTP client over the Elexon Insights API.

    Each public method returns a list of plain dataclasses already filtered
    to the fields this application cares about; it never leaks raw HTTP
    objects or the full upstream JSON to callers.
    """

    def __init__(self, base_url: str | None = None, session: requests.Session | None = None):
        self._base_url = (base_url or settings.ELEXON_API_BASE_URL).rstrip("/")
        self._session = session or requests.Session()

    def fetch_wind_actuals(self, start: date, end: date) -> list[ActualGenerationRecord]:
        """FUELHH actuals for national wind generation, filtered to
        fuelType=WIND, for the inclusive window [start, end]. Elexon rejects
        a publishDateTime span over 7 days (verified against the live API),
        so wider requests are split into <=7-day chunks and merged.
        """
        records: list[ActualGenerationRecord] = []
        for chunk_start, chunk_end in _chunk_date_range(start, end, max_days=7):
            params = {
                "publishDateTimeFrom": f"{chunk_start.isoformat()}T00:00:00Z",
                "publishDateTimeTo": f"{chunk_end.isoformat()}T23:59:59Z",
                "fuelType": "WIND",
                "format": "json",
            }
            payload = self._get("/datasets/FUELHH", params)
            rows = self._extract_rows(payload)

            for row in rows:
                fuel_type = row.get("fuelType")
                if fuel_type and fuel_type != "WIND":
                    continue
                start_time = row.get("startTime")
                generation = row.get("generation")
                if start_time is None or generation is None:
                    logger.warning("Skipping FUELHH row missing startTime/generation: %r", row)
                    continue
                records.append(
                    ActualGenerationRecord(
                        start_time=start_time,
                        settlement_period=row.get("settlementPeriod"),
                        generation_mw=float(generation),
                        fuel_type=fuel_type or "WIND",
                    )
                )
        return _deduplicate_actuals(records)

    def fetch_wind_forecasts(self, start: date, end: date) -> list[ForecastRecord]:
        """WINDFOR forecast publications relevant to delivery dates in
        [start, end]. Every publication is returned - selecting the
        decision-time version is a forecast-selection concern, not a client
        concern (see apps/forecasts/services/forecast_selection.py).

        Unlike FUELHH, WINDFOR is filtered by *publishDateTime*, not
        delivery startTime - a forecast published shortly before `start`
        can still cover a delivery period on `start`. We therefore widen
        the publish-time window a few days either side of the requested
        delivery range to make sure every decision-time-eligible
        publication, and the latest one published on each delivery day
        itself, is captured. Elexon rejects a publishDateTime span over 7
        days (verified against the live API), so a wide request is split
        into <=7-day chunks and the results merged.
        """
        publish_from = start - timedelta(days=4)
        publish_to = end + timedelta(days=1)

        records: list[ForecastRecord] = []
        for chunk_from, chunk_to in _chunk_date_range(publish_from, publish_to, max_days=7):
            params = {
                "publishDateTimeFrom": f"{chunk_from.isoformat()}T00:00:00Z",
                "publishDateTimeTo": f"{chunk_to.isoformat()}T00:00:00Z",
                "format": "json",
            }
            payload = self._get("/datasets/WINDFOR", params)
            rows = self._extract_rows(payload)

            for row in rows:
                start_time = row.get("startTime")
                publish_time = row.get("publishTime")
                generation = row.get("generation")
                if start_time is None or publish_time is None or generation is None:
                    logger.warning("Skipping WINDFOR row missing required fields: %r", row)
                    continue
                records.append(
                    ForecastRecord(
                        start_time=start_time,
                        publish_time=publish_time,
                        generation_mw=float(generation),
                    )
                )
        return _deduplicate_forecasts(records)

    # -- internal helpers ---------------------------------------------------

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        url = f"{self._base_url}{path}"
        last_error: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = self._session.get(url, params=params, timeout=_DEFAULT_TIMEOUT_SECONDS)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as exc:
                last_error = exc
                logger.warning("Elexon request failed (attempt %s/%s): %s", attempt, _MAX_RETRIES, exc)
                if attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_BACKOFF_SECONDS * attempt)
            except ValueError as exc:  # JSON decode error
                raise UpstreamDataError(f"Elexon returned a non-JSON response from {path}: {exc}") from exc
        raise UpstreamDataError(f"Elexon request to {path} failed after {_MAX_RETRIES} attempts: {last_error}")

    @staticmethod
    def _extract_rows(payload: Any) -> list[dict]:
        """Elexon Insights endpoints wrap results as either a bare list or
        an object with a `data` key, depending on dataset/version. Normalise
        both shapes to a list of row dicts."""
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, list):
                return data
        raise UpstreamDataError(f"Unexpected Elexon response shape: {type(payload)}")


def _chunk_date_range(start: date, end: date, max_days: int) -> list[tuple[date, date]]:
    """Split [start, end] into consecutive inclusive chunks of at most
    `max_days` days, used to stay within Elexon's per-request date-range
    limits (e.g. WINDFOR rejects a publishDateTime span over 7 days)."""
    if start > end:
        return []
    chunks: list[tuple[date, date]] = []
    chunk_start = start
    while chunk_start <= end:
        chunk_end = min(chunk_start + timedelta(days=max_days - 1), end)
        chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end + timedelta(days=1)
    return chunks


def _deduplicate_actuals(records: list[ActualGenerationRecord]) -> list[ActualGenerationRecord]:
    """Elexon occasionally re-publishes the same settlement period. Keep one
    record per startTime, preferring the last one seen (most recently
    returned by the API, treated as the latest revision)."""
    by_start_time: dict[str, ActualGenerationRecord] = {}
    for record in records:
        by_start_time[record.start_time] = record
    return sorted(by_start_time.values(), key=lambda r: r.start_time)


def _deduplicate_forecasts(records: list[ForecastRecord]) -> list[ForecastRecord]:
    """Keep one record per (startTime, publishTime) pair - duplicates with
    an identical publication carry no new information."""
    by_key: dict[tuple[str, str], ForecastRecord] = {}
    for record in records:
        by_key[(record.start_time, record.publish_time)] = record
    return sorted(by_key.values(), key=lambda r: (r.start_time, r.publish_time))
