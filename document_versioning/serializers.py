from rest_framework import serializers
from document_versioning.models import DocumentVersion, VersionDiff, VersionRetentionPolicy, VersionManifest, VersionArchiveRecord


class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = [
            "id",
            "file",
            "version_number",
            "filepath",
            "file_hash",
            "file_size",
            "mime_type",
            "checksum_sha256",
            "is_archived",
            "is_locked",
            "change_summary",
            "created_by",
            "created_at",
            "updated_at",
        ]


class VersionDiffSerializer(serializers.ModelSerializer):
    class Meta:
        model = VersionDiff
        fields = [
            "id",
            "file",
            "from_version",
            "to_version",
            "diff_content",
            "diff_html",
            "additions",
            "deletions",
            "similarity_ratio",
            "created_at",
        ]


class VersionRetentionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = VersionRetentionPolicy
        fields = [
            "id",
            "project_id",
            "client_name",
            "max_versions",
            "retention_days",
            "archive_after_days",
            "require_approval_for_delete",
            "created_at",
            "updated_at",
        ]


class VersionManifestSerializer(serializers.ModelSerializer):
    class Meta:
        model = VersionManifest
        fields = [
            "id",
            "version",
            "manifest_data",
            "checksum_algorithm",
            "signature",
            "signature_verified",
            "created_at",
        ]


class VersionArchiveRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = VersionArchiveRecord
        fields = [
            "id",
            "version",
            "archived_path",
            "archived_at",
            "archive_format",
            "size_bytes",
            "restored_at",
            "restored_by",
        ]
