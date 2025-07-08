# platform_data_insights/urls.py

from django.urls import path
from .views import PlatformInsightsView

urlpatterns = [
    path("", PlatformInsightsView.as_view(), name="platform-insights"),
]

