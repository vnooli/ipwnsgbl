from django.urls import path

from apps.forecasts.views.views import (
    DataStatusView,
    ForecastPublicationHistoryView,
    RefreshDataView,
    WindSeriesView,
)

urlpatterns = [
    path("wind-series/", WindSeriesView.as_view(), name="wind-series"),
    path(
        "publication-history/",
        ForecastPublicationHistoryView.as_view(),
        name="publication-history",
    ),
    path("status/", DataStatusView.as_view(), name="data-status"),
    path("refresh/", RefreshDataView.as_view(), name="refresh"),
]
