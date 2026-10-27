import json
from datetime import date
from unittest.mock import patch

from django.test import RequestFactory, TestCase

from apps.forecasts.repositories.elexon_client import ActualGenerationRecord, ForecastRecord
from apps.forecasts.views.views import WindSeriesView


class WindSeriesViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("apps.forecasts.repositories.forecast_repository.get_wind_forecasts")
    @patch("apps.forecasts.repositories.forecast_repository.get_wind_actuals")
    def test_returns_aligned_series_for_valid_range(self, mock_actuals, mock_forecasts):
        mock_actuals.return_value = [
            ActualGenerationRecord("2026-01-01T00:00:00Z", 1, 4100.0, "WIND")
        ]
        mock_forecasts.return_value = [
            ForecastRecord("2026-01-01T00:00:00Z", "2025-12-31T09:00:00Z", 4200.0)
        ]
        request = self.factory.get("/api/forecasts/wind-series/", {"start": "2026-01-01", "end": "2026-01-01"})
        response = WindSeriesView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["actualGenerationMw"], 4100.0)

    def test_rejects_range_outside_january_2026(self):
        request = self.factory.get("/api/forecasts/wind-series/", {"start": "2025-12-01", "end": "2025-12-02"})
        response = WindSeriesView.as_view()(request)
        self.assertEqual(response.status_code, 400)

    def test_rejects_start_after_end(self):
        request = self.factory.get("/api/forecasts/wind-series/", {"start": "2026-01-10", "end": "2026-01-01"})
        response = WindSeriesView.as_view()(request)
        self.assertEqual(response.status_code, 400)

    def test_rejects_missing_params(self):
        request = self.factory.get("/api/forecasts/wind-series/")
        response = WindSeriesView.as_view()(request)
        self.assertEqual(response.status_code, 400)
