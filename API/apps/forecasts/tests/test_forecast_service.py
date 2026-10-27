from datetime import date
from unittest.mock import patch

from django.test import TestCase

from apps.forecasts.repositories.elexon_client import ActualGenerationRecord, ForecastRecord
from apps.forecasts.services.forecast_service import get_aligned_wind_series


class TestGetAlignedWindSeries(TestCase):
    @patch("apps.forecasts.repositories.forecast_repository.get_wind_forecasts")
    @patch("apps.forecasts.repositories.forecast_repository.get_wind_actuals")
    def test_periods_outside_requested_window_are_filtered_out(self, mock_actuals, mock_forecasts):
        # The Elexon client deliberately widens its forecast fetch window
        # (to capture decision-time-eligible publications made a few days
        # before `start`), which can return forecast delivery periods
        # outside [start, end]. The service must filter those back out.
        mock_actuals.return_value = [
            ActualGenerationRecord("2026-01-05T00:00:00Z", 1, 4000.0, "WIND"),
        ]
        mock_forecasts.return_value = [
            ForecastRecord("2026-01-01T00:00:00Z", "2025-12-31T09:00:00Z", 3000.0),  # before window
            ForecastRecord("2026-01-05T00:00:00Z", "2026-01-04T09:00:00Z", 4100.0),  # in window
            ForecastRecord("2026-01-09T00:00:00Z", "2026-01-08T09:00:00Z", 5000.0),  # after window
        ]
        periods = get_aligned_wind_series(date(2026, 1, 5), date(2026, 1, 5))
        assert len(periods) == 1
        assert periods[0].start_time.date().isoformat() == "2026-01-05"
        assert periods[0].decision_forecast_mw == 4100.0
