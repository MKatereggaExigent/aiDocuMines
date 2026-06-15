from django.db import models
from core.models import File
import uuid


class RedliningRun(models.Model):
    """Tracks each document redlining (diff/comparison) request."""

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_id = models.CharField(max_length=255, db_index=True)
    service_id = models.CharField(max_length=255, db_index=True)
    client_name = models.CharField(max_length=255, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"RedliningRun {self.id} - {self.status}"


class RedliningResult(models.Model):
    """Stores the diff/comparison result between two files."""

    STATUS_CHOICES = [
        ('Processing', 'Processing'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(
        RedliningRun, on_delete=models.CASCADE, related_name="redlining_results"
    )
    original_file = models.ForeignKey(File, on_delete=models.CASCADE, related_name="redlining_originals")
    comparison_file = models.ForeignKey(File, on_delete=models.CASCADE, related_name="redlining_comparisons", null=True, blank=True)
    diff_output_path = models.CharField(max_length=1024, blank=True, null=True)
    diff_html = models.TextField(blank=True, null=True)
    redline_docx_path = models.CharField(max_length=1024, blank=True, null=True)
    redline_pdf_path = models.CharField(max_length=1024, blank=True, null=True)
    comparison_stats = models.JSONField(blank=True, null=True)
    author = models.CharField(max_length=255, blank=True, null=True)
    comparison_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Processing', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("original_file", "comparison_file", "run")

    def __str__(self):
        return f"RedliningResult {self.id} - {self.status}"
