from django.urls import path
from .views import FileUploadView, MetadataView, BulkFolderUploadView, FileDownloadView, health_check  # UniversalTaskStatusView,
from .task_statuses import UploadStatusView, MetadataStatusView # MetadataExtractionTriggerView
from core.views import AssociateTopicToFileView


from .views import (
    FileInsightView,
    RunSummaryView,
    ClientSummaryView,
    StorageLocationsView,
    ProjectSummaryView,
    ServiceSummaryView,
)

urlpatterns = [
    # ✅ File Upload Endpoint
    path("upload/", FileUploadView.as_view(), name="file-upload"),

    # ✅ Task Status (Universal)
    # path("task-status/", UniversalTaskStatusView.as_view(), name="universal-task-status"),

    # ✅ Bulk Folder Upload Endpoint
    path("upload/folder/", BulkFolderUploadView.as_view(), name="bulk-folder-upload"),  # ✅ New path

    # ✅ Upload Processing Status
    path("upload-status/", UploadStatusView.as_view(), name="upload-status"),

    # ✅ File Download
    path("download/", FileDownloadView.as_view(), name="file-download"),

    # ✅ Metadata for a Specific File
    path("metadata/", MetadataView.as_view(), name="metadata"),

    # ✅ Metadata Extraction Trigger
    # path("metadata/extract/", MetadataExtractionTriggerView.as_view(), name="metadata-extract"),

    # ✅ All Metadata Records
    path("metadata-status/", MetadataStatusView.as_view(), name="metadata-status"),
    
    # For document interrogation
    path('files/<int:file_id>/associate-topic/', AssociateTopicToFileView.as_view(), name='associate-topic'),


    # ✅ File Insight by file_id
    path("file-insight/", FileInsightView.as_view(), name="file-insight"),

    # ✅ Run summary by run_id
    path("run-summary/", RunSummaryView.as_view(), name="run-summary"),

    # ✅ Dashboard for logged-in client
    path("client-summary/", ClientSummaryView.as_view(), name="client-summary"),

    # ✅ File storage mapping
    path("storage-locations/", StorageLocationsView.as_view(), name="storage-locations"),

    # ✅ Filter files by project_id
    path("project-summary/", ProjectSummaryView.as_view(), name="project-summary"),

    # ✅ Filter files by service_id
    path("service-summary/", ServiceSummaryView.as_view(), name="service-summary"),



    # Health Checker
    path("health/", health_check, name="health_check"),
    
]
