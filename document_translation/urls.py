from django.urls import path
from .views import SubmitTranslationAPIView, CheckTranslationStatusAPIView, health_check
from .task_statuses import TranslationTaskStatusView, TranslationFileDownloadView  # ✅ Import new view

urlpatterns = [
    path("submit-translation/", SubmitTranslationAPIView.as_view(), name="submit-translation"),
    path("check-translation-status/", TranslationTaskStatusView.as_view(), name="check-translation-status"),
    path("download-file/", TranslationFileDownloadView.as_view(), name="download-file"),  # ✅ New file download endpoint
    # Health Checker
    path("health/", health_check, name="health_check"),
    ]
