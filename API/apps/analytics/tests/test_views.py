from unittest.mock import patch

from django.test import RequestFactory, TestCase

from apps.analytics.views.views import AccuracyMetricsView
from apps.forecasts.repositories.elexon_client import ActualGenerationRecord, ForecastRecord


class AccuracyMetricsViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("apps.forecasts.repositories.forecast_repository.get_wind_forecasts")
    @patch("apps.forecasts.repositories.forecast_repository.get_wind_actuals")
    def test_returns_metrics_and_interpretation(self, mock_actuals, mock_forecasts):
        mock_actuals.return_value = [ActualGenerationRecord("2026-01-01T00:00:00Z", 1, 4000.0, "WIND")]
        mock_forecasts.return_value = [
            ForecastRecord("2026-01-01T00:00:00Z", "2025-12-31T09:00:00Z", 4500.0)
        ]
        request = self.factory.get("/api/analytics/accuracy/", {"start": "2026-01-01", "end": "2026-01-01"})
        response = AccuracyMetricsView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["metrics"]["biasMw"], 500.0)
        self.assertIn("OVER-stated", response.data["procurementInterpretation"]["summary"])
        self.assertIn("does not account for", response.data["procurementInterpretation"]["disclaimer"])
