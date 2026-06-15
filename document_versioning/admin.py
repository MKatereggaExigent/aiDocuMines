from django.contrib import admin
from document_versioning.models import DocumentVersion, VersionDiff, VersionRetentionPolicy, VersionManifest, VersionArchiveRecord


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ("file", "version_number", "file_hash", "file_size", "is_archived", "is_locked", "created_by", "created_at")
    list_filter = ("is_archived", "is_locked", "created_at")
    search_fields = ("file__filename", "created_by", "file_hash", "checksum_sha256")


@admin.register(VersionDiff)
class VersionDiffAdmin(admin.ModelAdmin):
    list_display = ("file", "from_version", "to_version", "additions", "deletions", "similarity_ratio", "created_at")
    list_filter = ("created_at",)


@admin.register(VersionRetentionPolicy)
class VersionRetentionPolicyAdmin(admin.ModelAdmin):
    list_display = ("project_id", "client_name", "max_versions", "retention_days", "archive_after_days", "created_at")
    list_filter = ("created_at",)
    search_fields = ("project_id", "client_name")


@admin.register(VersionManifest)
class VersionManifestAdmin(admin.ModelAdmin):
    list_display = ("version", "checksum_algorithm", "signature_verified", "created_at")
    list_filter = ("signature_verified", "created_at")


@admin.register(VersionArchiveRecord)
class VersionArchiveRecordAdmin(admin.ModelAdmin):
    list_display = ("version", "archive_format", "size_bytes", "archived_at", "restored_at")
    list_filter = ("archive_format", "archived_at", "restored_at")
