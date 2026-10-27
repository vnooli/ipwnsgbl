"""Query: read-only request to fetch the aligned actual/forecast wind
generation series for a date range. A thin typed wrapper around the
service call, giving the view a single validated object to pass down."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from apps.forecasts.services import forecast_service
from apps.forecasts.services.forecast_selection import AlignedPeriod


@dataclass(frozen=True)
class WindSeriesQuery:
    start: date
    end: date
    cutoff_hour: int | None = None

    def execute(self) -> list[AlignedPeriod]:
        return forecast_service.get_aligned_wind_series(self.start, self.end, self.cutoff_hour)
