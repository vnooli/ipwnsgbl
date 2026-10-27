from django.urls import include, path

urlpatterns = [
    path("api/forecasts/", include("apps.forecasts.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
]
