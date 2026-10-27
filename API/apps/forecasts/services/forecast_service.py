"""Coordinates repository access and forecast-selection logic for the
forecasts app's use cases. Views call these functions; they never talk to
the repository or Elexon client directly."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from apps.forecasts.exceptions import InvalidParameterError
from apps.forecasts.repositories import cache as cache_repo
from apps.forecasts.repositories import forecast_repository
from apps.forecasts.services.forecast_selection import AlignedPeriod, align_periods

JANUARY_2026_START = date(2026, 1, 1)
JANUARY_2026_END = date(2026, 1, 31)


def validate_date_range(start: date, end: date) -> None:
    if start > end:
        raise InvalidParameterError(
            "The start date must be on or before the end date. Please adjust your date range."
        )
    if start < JANUARY_2026_START or end > JANUARY_2026_END:
        raise InvalidParameterError(
            "This dashboard currently covers January 2026 only "
            f"({JANUARY_2026_START.isoformat()} to {JANUARY_2026_END.isoformat()}). "
            "Please choose dates within that range."
        )


def get_aligned_wind_series(start: date, end: date, cutoff_hour: int | None = None) -> list[AlignedPeriod]:
    """Fetch actuals and forecasts for the window and return them aligned to
    shared delivery periods with the decision-time forecast selected.

    The Elexon forecast fetch deliberately widens its *publish*-time window
    (see `ElexonClient.fetch_wind_forecasts`) to capture decision-time
    eligible publications, which can also return forecasts whose *delivery*
    time falls outside [start, end]. Those are filtered back out here so the
    returned series never silently extends past the requested delivery
    window.
    """
    validate_date_range(start, end)
    actuals = forecast_repository.get_wind_actuals(start, end)
    forecasts = forecast_repository.get_wind_forecasts(start, end)
    periods = align_periods(actuals, forecasts, cutoff_hour)

    window_start = datetime.combine(start, time.min, tzinfo=timezone.utc)
    window_end = datetime.combine(end, time.min, tzinfo=timezone.utc) + timedelta(days=1)
    return [p for p in periods if window_start <= p.start_time < window_end]


def refresh_data(start: date, end: date) -> dict:
    """Force a refresh of cached Elexon data for the given window."""
    validate_date_range(start, end)
    cleared = cache_repo.invalidate()
    get_aligned_wind_series(start, end)
    return {"status": "refreshed", "cache_entries_cleared": cleared}


def get_data_status() -> dict:
    return cache_repo.status()
