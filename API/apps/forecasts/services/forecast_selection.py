"""Core business logic: aligning forecasts to delivery periods and selecting
the forecast version that was actually available at a procurement decision
cutoff. Deliberately independent of HTTP/Django so it is directly unit
testable (see apps/forecasts/tests/test_forecast_selection.py).

Decision-cutoff rule (documented assumption - see README "Decision cutoff
assumption"): the UK day-ahead auction gate closes late morning on D-1. The
assignment does not specify an exact cutoff, so this app uses a configurable
hour (`DECISION_CUTOFF_HOUR`, default 11:00) in Europe/London local time on
the day before delivery. For a delivery period with startTime on day D, the
cutoff instant is `DECISION_CUTOFF_HOUR:00` Europe/London on day D-1. Only
forecasts published strictly on or before that instant are eligible; a later
forecast is never used for the decision-time evaluation, though it may be
shown separately for comparison.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings

from apps.forecasts.repositories.elexon_client import ActualGenerationRecord, ForecastRecord

UK_TZ = ZoneInfo("Europe/London")
UTC = ZoneInfo("UTC")


def _parse_iso(value: str) -> datetime:
    """Parse an Elexon ISO-8601 timestamp into a timezone-aware UTC datetime.
    Elexon returns UTC timestamps (suffixed `Z` or `+00:00`); naive values are
    treated as UTC rather than silently compared against aware ones."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def decision_cutoff_for_delivery_date(delivery_date: date, cutoff_hour: int | None = None) -> datetime:
    """The decision cutoff instant (in UTC) for a given delivery date,
    computed from `DECISION_CUTOFF_HOUR` Europe/London on D-1. Using a
    timezone-aware local time and converting to UTC (rather than a fixed UTC
    offset) keeps the cutoff correct across the UK's GMT/BST transitions."""
    hour = settings.DECISION_CUTOFF_HOUR if cutoff_hour is None else cutoff_hour
    day_before = delivery_date - timedelta(days=1)
    local_cutoff = datetime.combine(day_before, time(hour=hour), tzinfo=UK_TZ)
    return local_cutoff.astimezone(UTC)


@dataclass(frozen=True)
class AlignedPeriod:
    start_time: datetime  # UTC
    actual_generation_mw: float | None
    decision_forecast_mw: float | None
    decision_forecast_publish_time: datetime | None
    latest_forecast_mw: float | None
    latest_forecast_publish_time: datetime | None
    has_actual: bool
    has_decision_forecast: bool


def _hour_bucket(moment: datetime) -> datetime:
    """Floor a delivery-period start time to its containing hour. WINDFOR
    publishes national wind forecasts at hourly resolution while FUELHH
    actuals are half-hourly; bucketing by hour lets a single hourly forecast
    value apply to both half-hour actual periods it covers, instead of the
    second (HH:30) period silently having no forecast at all."""
    return moment.replace(minute=0, second=0, microsecond=0)


def select_decision_time_forecast(
    forecasts_by_start: dict[datetime, list[ForecastRecord]],
    start_time: datetime,
    cutoff: datetime,
) -> ForecastRecord | None:
    """Among all forecast publications covering one delivery period's hour
    bucket, return the most recently published one that is still <= cutoff.
    Ties on publishTime (duplicate publications) are broken deterministically
    by preferring the highest generation value, since the repository already
    deduplicates and sorts by (startTime, publishTime).
    """
    candidates = forecasts_by_start.get(_hour_bucket(start_time), [])
    eligible = [f for f in candidates if _parse_iso(f.publish_time) <= cutoff]
    if not eligible:
        return None
    return max(eligible, key=lambda f: (_parse_iso(f.publish_time), f.generation_mw))


def align_periods(
    actuals: list[ActualGenerationRecord],
    forecasts: list[ForecastRecord],
    cutoff_hour: int | None = None,
) -> list[AlignedPeriod]:
    """Align actual (30-minute) and forecast (hourly) records to delivery
    periods driven by the actuals' half-hourly `startTime` grid, selecting -
    per period - the forecast that was available at that period's decision
    cutoff, plus the latest forecast ever published for the same hour (for
    comparison only; never used in decision-time accuracy metrics).

    WINDFOR's national forecast is published hourly while FUELHH actuals are
    half-hourly, so forecasts are bucketed by hour (see `_hour_bucket`) and
    applied to both half-hour periods within that hour, rather than requiring
    an exact timestamp match that would silently drop every HH:30 period.
    """
    actuals_by_start: dict[datetime, ActualGenerationRecord] = {}
    for a in actuals:
        actuals_by_start[_parse_iso(a.start_time)] = a

    forecasts_by_start: dict[datetime, list[ForecastRecord]] = {}
    for f in forecasts:
        forecasts_by_start.setdefault(_hour_bucket(_parse_iso(f.start_time)), []).append(f)

    all_starts = sorted(set(actuals_by_start) | set(forecasts_by_start))

    periods: list[AlignedPeriod] = []
    for start_time in all_starts:
        cutoff = decision_cutoff_for_delivery_date(start_time.astimezone(UK_TZ).date(), cutoff_hour)

        decision_forecast = select_decision_time_forecast(forecasts_by_start, start_time, cutoff)

        candidates = forecasts_by_start.get(_hour_bucket(start_time), [])
        latest_forecast = (
            max(candidates, key=lambda f: _parse_iso(f.publish_time)) if candidates else None
        )

        actual = actuals_by_start.get(start_time)

        periods.append(
            AlignedPeriod(
                start_time=start_time,
                actual_generation_mw=actual.generation_mw if actual else None,
                decision_forecast_mw=decision_forecast.generation_mw if decision_forecast else None,
                decision_forecast_publish_time=(
                    _parse_iso(decision_forecast.publish_time) if decision_forecast else None
                ),
                latest_forecast_mw=latest_forecast.generation_mw if latest_forecast else None,
                latest_forecast_publish_time=(
                    _parse_iso(latest_forecast.publish_time) if latest_forecast else None
                ),
                has_actual=actual is not None,
                has_decision_forecast=decision_forecast is not None,
            )
        )
    return periods
