from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.queries.accuracy_query import AccuracyQuery
from apps.forecasts.serializers.serializers import DateRangeParamsSerializer


class AccuracyMetricsView(APIView):
    """GET /api/analytics/accuracy/?start=2026-01-01&end=2026-01-31

    Forecast accuracy metrics (MAE, RMSE, bias, MAPE) over decision-time
    forecasts vs. actuals in the given window, plus procurement-relevant
    interpretation. Values are wind-forecast-derived estimates only - see
    README "Procurement interpretation": this endpoint does not know demand,
    other generation, or market prices.
    """

    def get(self, request):
        params = DateRangeParamsSerializer(data=request.query_params)
        start, end, cutoff_hour = params.validated()
        metrics = AccuracyQuery(start=start, end=end, cutoff_hour=cutoff_hour).execute()

        bias = metrics.bias_mw
        if bias is None:
            interpretation = "Insufficient data to assess directional bias for this window."
        elif bias > 0:
            interpretation = (
                "On average, decision-time forecasts OVER-stated wind generation by "
                f"{bias} MW per period. This implies the residual generation need from "
                "other sources was, on average, larger than the forecast suggested at "
                "decision time (assuming demand and other generation held as expected)."
            )
        elif bias < 0:
            interpretation = (
                "On average, decision-time forecasts UNDER-stated wind generation by "
                f"{abs(bias)} MW per period. This implies the residual generation need "
                "from other sources was, on average, smaller than the forecast "
                "suggested at decision time (assuming demand and other generation held "
                "as expected)."
            )
        else:
            interpretation = "Decision-time forecasts showed no net directional bias over this window."

        return Response(
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "metrics": {
                    "maeMw": metrics.mae_mw,
                    "rmseMw": metrics.rmse_mw,
                    "biasMw": metrics.bias_mw,
                    "mapePercent": metrics.mape_percent,
                    "sampleCountMaeRmseBias": metrics.sample_count_mae_rmse_bias,
                    "sampleCountMape": metrics.sample_count_mape,
                    "totalPeriods": metrics.total_periods,
                    "periodsMissingActual": metrics.periods_missing_actual,
                    "periodsMissingDecisionForecast": metrics.periods_missing_decision_forecast,
                },
                "procurementInterpretation": {
                    "summary": interpretation,
                    "disclaimer": (
                        "This is a wind-forecast-derived estimate only. It does not account "
                        "for electricity demand, other generation sources, or market prices, "
                        "and must not be used as a definitive purchase volume, financial loss, "
                        "or realised procurement cost."
                    ),
                },
            }
        )
