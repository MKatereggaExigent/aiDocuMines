from django.urls import path
from .views import (
    SubmitVersionAPIView,
    ListVersionsAPIView,
    GetVersionDiffAPIView,
    CompareVersionsDetailedView,
    CheckVersionStatusAPIView,
    DownloadVersionAPIView,
    RetentionPolicyView,
    VersionManifestView,
    ArchiveVersionView,
    RestoreVersionView,
    LockVersionView,
    health_check,
)

urlpatterns = [
    path("submit-version/", SubmitVersionAPIView.as_view(), name="submit-version"),
    path("list-versions/", ListVersionsAPIView.as_view(), name="list-versions"),
    path("version-diff/", GetVersionDiffAPIView.as_view(), name="version-diff"),
    path("compare-versions-detailed/", CompareVersionsDetailedView.as_view(), name="compare-versions-detailed"),
    path("check-version-status/", CheckVersionStatusAPIView.as_view(), name="check-version-status"),
    path("download-version/", DownloadVersionAPIView.as_view(), name="download-version"),
    path("retention-policy/", RetentionPolicyView.as_view(), name="retention-policy"),
    path("version-manifest/", VersionManifestView.as_view(), name="version-manifest"),
    path("archive-version/", ArchiveVersionView.as_view(), name="archive-version"),
    path("restore-version/", RestoreVersionView.as_view(), name="restore-version"),
    path("lock-version/", LockVersionView.as_view(), name="lock-version"),
    path("health/", health_check, name="health_check"),
]
