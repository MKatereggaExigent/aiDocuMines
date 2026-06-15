from django.urls import path
from .views import (
    SubmitRedliningAPIView,
    CheckRedliningStatusAPIView,
    DownloadRedliningResultAPIView,
    health_check,
)

urlpatterns = [
    path("submit-redlining/", SubmitRedliningAPIView.as_view(), name="submit-redlining"),
    path("check-redlining-status/", CheckRedliningStatusAPIView.as_view(), name="check-redlining-status"),
    path("download-redlining-result/", DownloadRedliningResultAPIView.as_view(), name="download-redlining-result"),
    path("health/", health_check, name="health_check"),
]
