from datetime import date

import pytest

from apps.forecasts.repositories.elexon_client import ActualGenerationRecord, ForecastRecord
from apps.forecasts.services.forecast_selection import (
    AlignedPeriod,
    align_periods,
    decision_cutoff_for_delivery_date,
    select_decision_time_forecast,
)


def _forecast(start, publish, generation):
    return ForecastRecord(start_time=start, publish_time=publish, generation_mw=generation)


def _actual(start, generation):
    return ActualGenerationRecord(start_time=start, settlement_period=None, generation_mw=generation, fuel_type="WIND")


class TestDecisionCutoff:
    def test_cutoff_is_hour_on_day_before_delivery_in_uk_time(self):
        cutoff = decision_cutoff_for_delivery_date(date(2026, 1, 15), cutoff_hour=11)
        # January: UK is on GMT (UTC+0), so 11:00 local == 11:00 UTC.
        assert cutoff.isoformat() == "2026-01-14T11:00:00+00:00"

    def test_cutoff_handles_bst_offset_correctly(self):
        # July: UK is on BST (UTC+1), so 11:00 local == 10:00 UTC.
        cutoff = decision_cutoff_for_delivery_date(date(2026, 7, 15), cutoff_hour=11)
        assert cutoff.isoformat() == "2026-07-14T10:00:00+00:00"


class TestSelectDecisionTimeForecast:
    def test_picks_latest_publish_on_or_before_cutoff(self):
        start = date(2026, 1, 15)
        from datetime import datetime, timezone

        start_dt = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        cutoff = decision_cutoff_for_delivery_date(start, cutoff_hour=11)
        forecasts_by_start = {
            start_dt: [
                _forecast("2026-01-15T12:00:00Z", "2026-01-14T08:00:00Z", 4000),
                _forecast("2026-01-15T12:00:00Z", "2026-01-14T10:30:00Z", 4200),  # eligible, latest <= cutoff
                _forecast("2026-01-15T12:00:00Z", "2026-01-14T12:00:00Z", 5000),  # published after cutoff
            ]
        }
        selected = select_decision_time_forecast(forecasts_by_start, start_dt, cutoff)
        assert selected is not None
        assert selected.generation_mw == 4200

    def test_never_selects_a_forecast_published_after_cutoff(self):
        from datetime import datetime, timezone

        start_dt = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        cutoff = decision_cutoff_for_delivery_date(date(2026, 1, 15), cutoff_hour=11)
        forecasts_by_start = {
            start_dt: [_forecast("2026-01-15T12:00:00Z", "2026-01-14T11:00:01Z", 9999)],
        }
        selected = select_decision_time_forecast(forecasts_by_start, start_dt, cutoff)
        assert selected is None

    def test_returns_none_when_no_eligible_forecast_exists(self):
        from datetime import datetime, timezone

        start_dt = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        cutoff = decision_cutoff_for_delivery_date(date(2026, 1, 15), cutoff_hour=11)
        assert select_decision_time_forecast({}, start_dt, cutoff) is None


class TestAlignPeriods:
    def test_aligns_actual_and_forecast_on_matching_start_time(self):
        actuals = [_actual("2026-01-15T12:00:00Z", 4100.0)]
        forecasts = [_forecast("2026-01-15T12:00:00Z", "2026-01-14T09:00:00Z", 4200.0)]
        periods = align_periods(actuals, forecasts, cutoff_hour=11)
        assert len(periods) == 1
        p = periods[0]
        assert p.has_actual and p.has_decision_forecast
        assert p.actual_generation_mw == 4100.0
        assert p.decision_forecast_mw == 4200.0

    def test_period_missing_actual_is_flagged_not_defaulted(self):
        forecasts = [_forecast("2026-01-15T12:00:00Z", "2026-01-14T09:00:00Z", 4200.0)]
        periods = align_periods([], forecasts, cutoff_hour=11)
        assert len(periods) == 1
        assert periods[0].has_actual is False
        assert periods[0].actual_generation_mw is None

    def test_period_missing_forecast_is_flagged_not_defaulted(self):
        actuals = [_actual("2026-01-15T12:00:00Z", 4100.0)]
        periods = align_periods(actuals, [], cutoff_hour=11)
        assert len(periods) == 1
        assert periods[0].has_decision_forecast is False
        assert periods[0].decision_forecast_mw is None

    def test_latest_forecast_is_separate_from_decision_time_forecast(self):
        actuals = [_actual("2026-01-15T12:00:00Z", 4100.0)]
        forecasts = [
            _forecast("2026-01-15T12:00:00Z", "2026-01-14T09:00:00Z", 4200.0),  # decision-time eligible
            _forecast("2026-01-15T12:00:00Z", "2026-01-15T10:00:00Z", 4300.0),  # published after cutoff, latest
        ]
        periods = align_periods(actuals, forecasts, cutoff_hour=11)
        p = periods[0]
        assert p.decision_forecast_mw == 4200.0
        assert p.latest_forecast_mw == 4300.0

    def test_empty_input_returns_empty_list(self):
        assert align_periods([], [], cutoff_hour=11) == []

    def test_hourly_forecast_applies_to_both_half_hour_actual_periods(self):
        # WINDFOR is published hourly while FUELHH actuals are half-hourly;
        # an exact-timestamp match would silently drop every HH:30 period.
        actuals = [
            _actual("2026-01-15T12:00:00Z", 4000.0),
            _actual("2026-01-15T12:30:00Z", 4050.0),
        ]
        forecasts = [_forecast("2026-01-15T12:00:00Z", "2026-01-14T09:00:00Z", 4200.0)]
        periods = align_periods(actuals, forecasts, cutoff_hour=11)
        assert len(periods) == 2
        assert all(p.decision_forecast_mw == 4200.0 for p in periods)
        assert all(p.has_decision_forecast for p in periods)
