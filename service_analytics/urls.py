from django.urls import path
from service_analytics.views import (
    ServiceAnalyticsOverviewAPIView,
    RecentActivityAPIView,
)

urlpatterns = [
    path('overview/', ServiceAnalyticsOverviewAPIView.as_view(), name='service-analytics-overview'),
    path('recent-activity/', RecentActivityAPIView.as_view(), name='service-analytics-recent-activity'),
]

