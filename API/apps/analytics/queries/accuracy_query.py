from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from apps.analytics.services.accuracy_metrics import AccuracyMetrics, calculate_accuracy_metrics
from apps.forecasts.services.forecast_service import get_aligned_wind_series


@dataclass(frozen=True)
class AccuracyQuery:
    start: date
    end: date
    cutoff_hour: int | None = None

    def execute(self) -> AccuracyMetrics:
        periods = get_aligned_wind_series(self.start, self.end, self.cutoff_hour)
        return calculate_accuracy_metrics(periods)
