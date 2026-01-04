"""
Document Classification Serializers

Serializers for clustering/classification models and input validation.
"""

from rest_framework import serializers
from document_classification.models import ClusteringRun, ClusterResult, ClusterFile, ClusterStorage


class ClusterFileSerializer(serializers.ModelSerializer):
    """Serializer for individual files in a clustering run."""
    
    class Meta:
        model = ClusterFile
        fields = [
            'id', 'filename', 'filepath', 'file_type', 'file_extension',
            'file_size', 'cluster_id', 'status', 'error_message',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ClusterResultSerializer(serializers.ModelSerializer):
    """Serializer for cluster results with nested files."""
    files = ClusterFileSerializer(many=True, read_only=True)
    
    class Meta:
        model = ClusterResult
        fields = [
            'id', 'cluster_id', 'cluster_label', 'file_count',
            'description', 'keywords', 'files', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ClusteringRunSerializer(serializers.ModelSerializer):
    """Serializer for clustering runs with nested results."""
    cluster_results = ClusterResultSerializer(many=True, read_only=True)
    cluster_files = ClusterFileSerializer(many=True, read_only=True)
    
    class Meta:
        model = ClusteringRun
        fields = [
            'id', 'project_id', 'service_id', 'client_name',
            'clustering_method', 'embedding_model', 'generate_descriptions',
            'status', 'error_message',
            'optimal_clusters', 'calinski_harabasz_index', 'davies_bouldin_index',
            'input_tokens', 'output_tokens', 'total_tokens',
            'media_duration', 'price', 'elapsed_time',
            'cluster_results', 'cluster_files',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'error_message', 'optimal_clusters',
            'calinski_harabasz_index', 'davies_bouldin_index',
            'input_tokens', 'output_tokens', 'total_tokens',
            'media_duration', 'price', 'elapsed_time',
            'created_at', 'updated_at'
        ]


class ClusteringRunListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing clustering runs."""
    file_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ClusteringRun
        fields = [
            'id', 'project_id', 'service_id', 'client_name',
            'clustering_method', 'status', 'optimal_clusters',
            'file_count', 'created_at', 'updated_at'
        ]
    
    def get_file_count(self, obj):
        return obj.cluster_files.count()


class ClusterStorageSerializer(serializers.ModelSerializer):
    """Serializer for cluster storage locations."""
    
    class Meta:
        model = ClusterStorage
        fields = [
            'id', 'run', 'upload_storage_location',
            'embeddings_storage_location', 'results_storage_location',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# Input Serializers for API validation

class ClusteringSubmitSerializer(serializers.Serializer):
    """Serializer for clustering submission request."""
    file_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        min_length=2,
        help_text="List of file IDs to cluster (minimum 2 files)"
    )
    project_id = serializers.CharField(required=True, max_length=255)
    service_id = serializers.CharField(required=True, max_length=255)
    clustering_method = serializers.ChoiceField(
        choices=['agglomerative', 'dbscan', 'kmeans', 'spectral'],
        default='agglomerative',
        required=False
    )
    embedding_model = serializers.ChoiceField(
        choices=['bert-base-uncased', 'roberta-base', 'legal-bert'],
        default='bert-base-uncased',
        required=False
    )
    generate_descriptions = serializers.BooleanField(default=True, required=False)
    
    def validate_file_ids(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("At least 2 files are required for clustering.")
        return value


class ClusteringStatusSerializer(serializers.Serializer):
    """Serializer for clustering status response."""
    run_id = serializers.UUIDField()
    status = serializers.CharField()
    optimal_clusters = serializers.IntegerField()
    file_count = serializers.IntegerField()
    completed_files = serializers.IntegerField()
    failed_files = serializers.IntegerField()


class ClusteringResultsSerializer(serializers.Serializer):
    """Serializer for clustering results response."""
    run_id = serializers.UUIDField()
    status = serializers.CharField()
    clustering_method = serializers.CharField()
    optimal_clusters = serializers.IntegerField()
    calinski_harabasz_index = serializers.FloatField()
    davies_bouldin_index = serializers.FloatField()
    clusters = ClusterResultSerializer(many=True)
    elapsed_time = serializers.DictField()
    price = serializers.DictField()

