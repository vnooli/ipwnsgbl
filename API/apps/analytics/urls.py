from django.urls import path

from apps.analytics.views.views import AccuracyMetricsView

urlpatterns = [
    path("accuracy/", AccuracyMetricsView.as_view(), name="accuracy-metrics"),
]
