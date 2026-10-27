from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.forecasts.commands.refresh_data_command import RefreshDataCommand
from apps.forecasts.queries.wind_series_query import WindSeriesQuery
from apps.forecasts.serializers.serializers import AlignedPeriodSerializer, DateRangeParamsSerializer
from apps.forecasts.services import forecast_service


class WindSeriesView(APIView):
    """GET /api/forecasts/wind-series/?start=2026-01-01&end=2026-01-07

    Returns actual vs. decision-time-forecast wind generation aligned to
    30-minute delivery periods, for the given January 2026 date range.
    """

    def get(self, request):
        params = DateRangeParamsSerializer(data=request.query_params)
        start, end, cutoff_hour = params.validated()
        periods = WindSeriesQuery(start=start, end=end, cutoff_hour=cutoff_hour).execute()
        data = AlignedPeriodSerializer(periods, many=True).data
        return Response({"start": start.isoformat(), "end": end.isoformat(), "count": len(data), "results": data})


class ForecastPublicationHistoryView(APIView):
    """GET /api/forecasts/publication-history/?start=2026-01-01&end=2026-01-01

    Returns, per delivery period, both the decision-time forecast and the
    latest-available forecast, so the UI can show the publication-time
    distinction explicitly without re-deriving it client-side.
    """

    def get(self, request):
        params = DateRangeParamsSerializer(data=request.query_params)
        start, end, cutoff_hour = params.validated()
        periods = WindSeriesQuery(start=start, end=end, cutoff_hour=cutoff_hour).execute()
        data = AlignedPeriodSerializer(periods, many=True).data
        return Response({"start": start.isoformat(), "end": end.isoformat(), "results": data})


class DataStatusView(APIView):
    """GET /api/forecasts/status/ - cache/data-source status for the UI's
    "latest available data" indicator."""

    def get(self, request):
        return Response(forecast_service.get_data_status())


class RefreshDataView(APIView):
    """POST /api/forecasts/refresh/ {"start": "...", "end": "..."}

    Triggers a controlled re-fetch of Elexon data for the given window,
    bypassing the in-memory cache.
    """

    def post(self, request):
        params = DateRangeParamsSerializer(data=request.data)
        start, end, _ = params.validated()
        result = RefreshDataCommand(start=start, end=end).execute()
        return Response(result)
