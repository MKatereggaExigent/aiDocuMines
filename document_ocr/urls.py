from django.urls import path
from .views import SubmitOCRAPIView, CheckOCRStatusAPIView, health_check
from .task_statuses import OCRTaskStatusView, OCRFileDownloadView  # ✅ Import new views

urlpatterns = [
    path("submit-ocr/", SubmitOCRAPIView.as_view(), name="submit-ocr"),
    path("check-ocr-status/", OCRTaskStatusView.as_view(), name="check-ocr-status"),  # ✅ Updated to use OCRTaskStatusView
    path("download-file/", OCRFileDownloadView.as_view(), name="download-file"),  # ✅ New file download endpoint
    # Health Checker
    path("health/", health_check, name="health_check"),
]
