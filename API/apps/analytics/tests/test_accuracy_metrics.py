from datetime import datetime, timezone

from apps.analytics.services.accuracy_metrics import calculate_accuracy_metrics
from apps.forecasts.services.forecast_selection import AlignedPeriod


def _period(actual, forecast, start_hour=0):
    return AlignedPeriod(
        start_time=datetime(2026, 1, 1, start_hour, tzinfo=timezone.utc),
        actual_generation_mw=actual,
        decision_forecast_mw=forecast,
        decision_forecast_publish_time=None,
        latest_forecast_mw=forecast,
        latest_forecast_publish_time=None,
        has_actual=actual is not None,
        has_decision_forecast=forecast is not None,
    )


class TestAccuracyMetrics:
    def test_mae_rmse_bias_on_simple_series(self):
        periods = [_period(100, 110, 0), _period(200, 190, 1)]  # errors: +10, -10
        m = calculate_accuracy_metrics(periods)
        assert m.mae_mw == 10.0
        assert m.rmse_mw == 10.0
        assert m.bias_mw == 0.0
        assert m.sample_count_mae_rmse_bias == 2

    def test_bias_sign_convention_is_forecast_minus_actual(self):
        periods = [_period(100, 150, 0)]  # forecast over-predicts by 50
        m = calculate_accuracy_metrics(periods)
        assert m.bias_mw == 50.0

    def test_mape_excludes_zero_actual_periods(self):
        periods = [_period(0, 50, 0), _period(100, 110, 1)]
        m = calculate_accuracy_metrics(periods)
        # only the second period (nonzero actual) contributes to MAPE
        assert m.sample_count_mape == 1
        assert m.mape_percent == 10.0

    def test_missing_values_are_excluded_not_treated_as_zero(self):
        periods = [_period(100, 110, 0), _period(None, 120, 1), _period(100, None, 2)]
        m = calculate_accuracy_metrics(periods)
        assert m.sample_count_mae_rmse_bias == 1
        assert m.periods_missing_actual == 1
        assert m.periods_missing_decision_forecast == 1
        assert m.total_periods == 3

    def test_empty_dataset_returns_none_metrics_not_zero(self):
        m = calculate_accuracy_metrics([])
        assert m.mae_mw is None
        assert m.rmse_mw is None
        assert m.bias_mw is None
        assert m.mape_percent is None
        assert m.sample_count_mae_rmse_bias == 0

    def test_all_missing_returns_none_metrics(self):
        periods = [_period(None, 100, 0), _period(100, None, 1)]
        m = calculate_accuracy_metrics(periods)
        assert m.mae_mw is None
        assert m.sample_count_mae_rmse_bias == 0
        assert m.total_periods == 2
