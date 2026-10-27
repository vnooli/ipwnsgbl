from __future__ import annotations

from datetime import date

from rest_framework import serializers

from apps.forecasts.exceptions import InvalidParameterError
from apps.forecasts.services.forecast_selection import AlignedPeriod


class DateRangeParamsSerializer(serializers.Serializer):
    start = serializers.DateField(required=True)
    end = serializers.DateField(required=True)
    cutoff_hour = serializers.IntegerField(required=False, min_value=0, max_value=23, allow_null=True)

    def validated(self) -> tuple[date, date, int | None]:
        if not self.is_valid():
            raise InvalidParameterError(_format_errors_for_users(self.errors))
        data = self.validated_data
        return data["start"], data["end"], data.get("cutoff_hour")


_FIELD_LABELS = {"start": "start date", "end": "end date", "cutoff_hour": "cutoff hour"}


def _format_errors_for_users(errors: dict) -> str:
    """Turn DRF's raw error dict (e.g. {'start': [ErrorDetail('This field
    is required.')]}) into a single readable sentence, instead of exposing
    DRF's internal representation directly to the UI."""
    parts = []
    for field, field_errors in errors.items():
        label = _FIELD_LABELS.get(field, field)
        message = str(field_errors[0]) if field_errors else "is invalid"
        # DRF's default messages are already lowercase-first and readable
        # ("This field is required." -> keep as-is, just prefix the label).
        parts.append(f"{label.capitalize()}: {message}")
    return " ".join(parts) if parts else "One or more parameters are invalid."


class AlignedPeriodSerializer(serializers.Serializer):
    startTime = serializers.SerializerMethodField()
    actualGenerationMw = serializers.SerializerMethodField()
    decisionForecastMw = serializers.SerializerMethodField()
    decisionForecastPublishTime = serializers.SerializerMethodField()
    latestForecastMw = serializers.SerializerMethodField()
    latestForecastPublishTime = serializers.SerializerMethodField()
    hasActual = serializers.BooleanField(source="has_actual")
    hasDecisionForecast = serializers.BooleanField(source="has_decision_forecast")
    forecastErrorMw = serializers.SerializerMethodField()
    absoluteErrorMw = serializers.SerializerMethodField()

    def get_startTime(self, obj: AlignedPeriod) -> str:
        return obj.start_time.isoformat()

    def get_actualGenerationMw(self, obj: AlignedPeriod) -> float | None:
        return obj.actual_generation_mw

    def get_decisionForecastMw(self, obj: AlignedPeriod) -> float | None:
        return obj.decision_forecast_mw

    def get_decisionForecastPublishTime(self, obj: AlignedPeriod) -> str | None:
        return obj.decision_forecast_publish_time.isoformat() if obj.decision_forecast_publish_time else None

    def get_latestForecastMw(self, obj: AlignedPeriod) -> float | None:
        return obj.latest_forecast_mw

    def get_latestForecastPublishTime(self, obj: AlignedPeriod) -> str | None:
        return obj.latest_forecast_publish_time.isoformat() if obj.latest_forecast_publish_time else None

    def get_forecastErrorMw(self, obj: AlignedPeriod) -> float | None:
        if obj.decision_forecast_mw is None or obj.actual_generation_mw is None:
            return None
        return round(obj.decision_forecast_mw - obj.actual_generation_mw, 3)

    def get_absoluteErrorMw(self, obj: AlignedPeriod) -> float | None:
        err = self.get_forecastErrorMw(obj)
        return abs(err) if err is not None else None
