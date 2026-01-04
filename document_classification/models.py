"""
Document Classification Models

Multi-tenant document clustering/classification with RBAC support.
Follows the pattern of document_ocr and document_anonymizer apps.
"""

from django.db import models
from django.contrib.auth import get_user_model
from core.models import File
import uuid

User = get_user_model()


class ClusteringRun(models.Model):
    """
    Tracks each document clustering/classification request.
    Multi-tenant: Isolated by client.
    """
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed')
    ]

    CLUSTERING_METHOD_CHOICES = [
        ('agglomerative', 'Agglomerative Clustering'),
        ('dbscan', 'DBSCAN'),
        ('kmeans', 'K-Means'),
        ('spectral', 'Spectral Clustering'),
    ]

    EMBEDDING_MODEL_CHOICES = [
        ('bert-base-uncased', 'BERT Base Uncased'),
        ('roberta-base', 'RoBERTa Base'),
        ('legal-bert', 'Legal BERT'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Multi-tenancy
    client = models.ForeignKey(
        'custom_authentication.Client', 
        on_delete=models.CASCADE, 
        related_name='clustering_runs',
        null=True, blank=True
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clustering_runs', null=True, blank=True)
    
    # Project context
    project_id = models.CharField(max_length=255, db_index=True)
    service_id = models.CharField(max_length=255, db_index=True)
    client_name = models.CharField(max_length=255, db_index=True)
    
    # Clustering configuration
    clustering_method = models.CharField(
        max_length=50, 
        choices=CLUSTERING_METHOD_CHOICES, 
        default='agglomerative',
        db_index=True
    )
    embedding_model = models.CharField(
        max_length=50, 
        choices=EMBEDDING_MODEL_CHOICES, 
        default='bert-base-uncased'
    )
    generate_descriptions = models.BooleanField(default=True)
    
    # Status and results
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', db_index=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Clustering results
    optimal_clusters = models.IntegerField(default=0)
    calinski_harabasz_index = models.FloatField(default=0.0)
    davies_bouldin_index = models.FloatField(default=0.0)
    
    # Token usage and pricing
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    media_duration = models.FloatField(default=0.0)
    price = models.JSONField(default=dict)
    
    # Timing
    elapsed_time = models.JSONField(default=dict)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'document_classification_run'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', '-created_at']),
            models.Index(fields=['client', 'status']),
            models.Index(fields=['project_id', 'service_id']),
        ]

    def __str__(self):
        return f"ClusteringRun {self.id} - {self.status} ({self.clustering_method})"


class ClusterResult(models.Model):
    """
    Stores the clustering result for a specific cluster.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(ClusteringRun, on_delete=models.CASCADE, related_name='cluster_results')
    
    cluster_id = models.IntegerField()
    cluster_label = models.CharField(max_length=500, blank=True, null=True)  # AI-generated description
    file_count = models.IntegerField(default=0)
    
    # Cluster metadata
    description = models.TextField(blank=True, null=True)
    keywords = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'document_classification_cluster_result'
        ordering = ['cluster_id']
        unique_together = ['run', 'cluster_id']

    def __str__(self):
        return f"Cluster {self.cluster_id} - {self.cluster_label or 'No Label'}"


class ClusterFile(models.Model):
    """
    Stores details of each file in a clustering run and its assigned cluster.
    """
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
        ('Unsupported', 'Unsupported File Type')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(ClusteringRun, on_delete=models.CASCADE, related_name='cluster_files')
    original_file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='clustering_results', null=True, blank=True)
    cluster_result = models.ForeignKey(ClusterResult, on_delete=models.SET_NULL, null=True, blank=True, related_name='files')
    
    # File info (for uploaded files not in core.File)
    filepath = models.CharField(max_length=1024)
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=100, blank=True, null=True)
    file_extension = models.CharField(max_length=20, blank=True, null=True)
    file_size = models.FloatField(default=0.0)  # Size in MB

    # Clustering assignment
    cluster_id = models.IntegerField(null=True, blank=True)

    # Extracted content
    extracted_text = models.TextField(blank=True, null=True)

    # Embedding (stored as JSON for flexibility)
    embedding = models.JSONField(blank=True, null=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', db_index=True)
    error_message = models.TextField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'document_classification_cluster_file'
        ordering = ['filename']

    def __str__(self):
        return f"{self.filename} - Cluster {self.cluster_id}"


class ClusterStorage(models.Model):
    """
    Stores file paths for clustering artifacts (embeddings, results, etc.).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(ClusteringRun, on_delete=models.CASCADE, related_name='storages')

    # Storage locations
    upload_storage_location = models.CharField(max_length=1024, blank=True, null=True)
    embeddings_storage_location = models.CharField(max_length=1024, blank=True, null=True)
    results_storage_location = models.CharField(max_length=1024, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'document_classification_storage'

    def __str__(self):
        return f"Storage for Run {self.run_id}"

