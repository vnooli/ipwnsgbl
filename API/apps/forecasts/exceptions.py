"""Shared exception types and a DRF exception handler that keeps internal
details (stack traces, upstream Elexon error bodies, credentials) out of
API responses while still returning a structured, actionable error."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


class UpstreamDataError(Exception):
    """Raised when the Elexon API is unreachable, times out, or returns a
    response we cannot parse."""


class InvalidParameterError(Exception):
    """Raised when request parameters fail domain-level validation."""


def api_exception_handler(exc, context):
    if isinstance(exc, UpstreamDataError):
        # `detail` carries the technical cause (dataset path, retry count,
        # the underlying exception) for API consumers/logs/debugging.
        # `message` is a short, non-technical sentence safe to show directly
        # to an end user in the dashboard - it never repeats internal
        # details like upstream URLs or exception text.
        return Response(
            {
                "error": "upstream_unavailable",
                "message": "The Elexon data service is temporarily unavailable. Please try again in a moment.",
                "detail": str(exc),
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if isinstance(exc, InvalidParameterError):
        # Validation messages (see forecast_service.validate_date_range and
        # DateRangeParamsSerializer) are already written to be user-facing,
        # so `message` and `detail` are the same here.
        message = str(exc)
        return Response(
            {"error": "invalid_parameter", "message": message, "detail": message},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return exception_handler(exc, context)
