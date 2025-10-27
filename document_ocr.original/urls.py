from django.urls import path
from .views import SubmitOCRAPIView, CheckOCRStatusAPIView, health_check
from .task_statuses import OCRTaskStatusView, OCRFileDownloadView  # Import new views

urlpatterns = [
    # OCR Processing Endpoints
    path("submit-ocr/", SubmitOCRAPIView.as_view(), name="submit-ocr"),
    path("check-ocr-status/", CheckOCRStatusAPIView.as_view(), name="check-ocr-status"),  # Updated to use CheckOCRStatusAPIView
    path("ocr-task-status/", OCRTaskStatusView.as_view(), name="ocr-task-status"),  # New endpoint for checking OCR task status
    path("download-file/", OCRFileDownloadView.as_view(), name="download-file"),  # New endpoint for file download

    # Health Check Endpoint
    path("health/", health_check, name="health_check"),
]

