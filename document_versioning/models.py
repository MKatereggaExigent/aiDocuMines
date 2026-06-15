from django.db import models
from core.models import File
import uuid


class DocumentVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name="doc_version_versions")
    version_number = models.IntegerField()
    filepath = models.CharField(max_length=1024)
    file_hash = models.CharField(max_length=32)
    file_size = models.BigIntegerField(blank=True, null=True)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True, null=True)
    is_archived = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    change_summary = models.TextField(blank=True)
    created_by = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["version_number"]
        unique_together = ("file", "version_number")

    def __str__(self):
        return f"v{self.version_number} of {self.file.filename}"


class VersionDiff(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name="doc_version_diffs")
    from_version = models.ForeignKey(
        DocumentVersion, on_delete=models.CASCADE, related_name="from_diffs"
    )
    to_version = models.ForeignKey(
        DocumentVersion, on_delete=models.CASCADE, related_name="to_diffs"
    )
    diff_content = models.TextField()
    diff_html = models.TextField()
    additions = models.IntegerField(default=0)
    deletions = models.IntegerField(default=0)
    similarity_ratio = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Diff v{self.from_version.version_number} -> v{self.to_version.version_number}"


class VersionRetentionPolicy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_id = models.CharField(max_length=255, db_index=True)
    client_name = models.CharField(max_length=255, db_index=True)
    max_versions = models.IntegerField(default=10)
    retention_days = models.IntegerField(default=365)
    archive_after_days = models.IntegerField(default=180)
    require_approval_for_delete = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Version retention policies"
        unique_together = ('project_id', 'client_name')

    def __str__(self):
        return f"RetentionPolicy - {self.project_id} ({self.max_versions} versions, {self.retention_days} days)"


class VersionManifest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.ForeignKey(DocumentVersion, on_delete=models.CASCADE, related_name='manifests')
    manifest_data = models.JSONField()
    checksum_algorithm = models.CharField(max_length=20, default='SHA256')
    signature = models.TextField(blank=True, null=True)
    signature_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Manifest v{self.version.version_number} - {self.version.file.filename}"


class VersionArchiveRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.ForeignKey(DocumentVersion, on_delete=models.CASCADE, related_name='archive_records')
    archived_path = models.CharField(max_length=1024)
    archived_at = models.DateTimeField(auto_now_add=True)
    archive_format = models.CharField(max_length=20, default='PDF/A')
    size_bytes = models.BigIntegerField(blank=True, null=True)
    restored_at = models.DateTimeField(blank=True, null=True)
    restored_by = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Archive v{self.version.version_number} at {self.archived_path}"
