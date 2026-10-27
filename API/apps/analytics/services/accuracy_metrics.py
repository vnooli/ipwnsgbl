"""Forecast accuracy metrics, calculated purely from aligned periods.
Deliberately decoupled from Django/HTTP and from the forecasts app's
selection logic so it is independently unit testable (and reusable if the
UI ever needs daily vs. settlement-period resolution).

Sign convention: error = forecast - actual. A positive error means the
forecast OVER-stated wind generation (so the actual residual demand that
needed to be met from other sources was likely larger than the forecast
implied); a negative error means the forecast UNDER-stated wind generation.
Bias is the mean of signed errors - a persistent positive bias indicates the
forecast systematically over-predicts wind.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from apps.forecasts.services.forecast_selection import AlignedPeriod


@dataclass(frozen=True)
class AccuracyMetrics:
    mae_mw: float | None
    rmse_mw: float | None
    bias_mw: float | None
    mape_percent: float | None
    sample_count_mae_rmse_bias: int
    sample_count_mape: int
    total_periods: int
    periods_missing_actual: int
    periods_missing_decision_forecast: int


def calculate_accuracy_metrics(periods: list[AlignedPeriod]) -> AccuracyMetrics:
    """Compute MAE, RMSE, bias and MAPE over periods that have BOTH an
    actual and a decision-time forecast. Periods missing either value are
    excluded from every metric and counted explicitly rather than treated
    as zero error, since treating a missing value as zero would silently
    understate forecast error.
    """
    usable = [
        p for p in periods
        if p.actual_generation_mw is not None and p.decision_forecast_mw is not None
    ]
    missing_actual = sum(1 for p in periods if p.actual_generation_mw is None)
    missing_forecast = sum(1 for p in periods if p.decision_forecast_mw is None)

    if not usable:
        return AccuracyMetrics(
            mae_mw=None,
            rmse_mw=None,
            bias_mw=None,
            mape_percent=None,
            sample_count_mae_rmse_bias=0,
            sample_count_mape=0,
            total_periods=len(periods),
            periods_missing_actual=missing_actual,
            periods_missing_decision_forecast=missing_forecast,
        )

    errors = [p.decision_forecast_mw - p.actual_generation_mw for p in usable]  # type: ignore[operator]
    abs_errors = [abs(e) for e in errors]

    mae = sum(abs_errors) / len(abs_errors)
    rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
    bias = sum(errors) / len(errors)

    # MAPE only over periods with nonzero actual generation - otherwise the
    # percentage error is undefined/meaningless (division by zero or a huge
    # spurious value for near-zero wind output).
    nonzero = [(e, p.actual_generation_mw) for e, p in zip(errors, usable) if p.actual_generation_mw]
    mape = (
        sum(abs(e) / actual for e, actual in nonzero) / len(nonzero) * 100
        if nonzero
        else None
    )

    return AccuracyMetrics(
        mae_mw=round(mae, 3),
        rmse_mw=round(rmse, 3),
        bias_mw=round(bias, 3),
        mape_percent=round(mape, 3) if mape is not None else None,
        sample_count_mae_rmse_bias=len(usable),
        sample_count_mape=len(nonzero),
        total_periods=len(periods),
        periods_missing_actual=missing_actual,
        periods_missing_decision_forecast=missing_forecast,
    )
