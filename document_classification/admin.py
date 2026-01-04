"""
Document Classification Admin

Django admin configuration for document clustering/classification models.
"""

from django.contrib import admin
from document_classification.models import ClusteringRun, ClusterResult, ClusterFile, ClusterStorage


class ClusterFileInline(admin.TabularInline):
    """Inline admin for ClusterFile."""
    model = ClusterFile
    extra = 0
    readonly_fields = ['id', 'filename', 'filepath', 'cluster_id', 'status', 'created_at']
    fields = ['filename', 'cluster_id', 'status', 'error_message']
    can_delete = False


class ClusterResultInline(admin.TabularInline):
    """Inline admin for ClusterResult."""
    model = ClusterResult
    extra = 0
    readonly_fields = ['id', 'cluster_id', 'cluster_label', 'file_count', 'created_at']
    fields = ['cluster_id', 'cluster_label', 'file_count', 'description']
    can_delete = False


@admin.register(ClusteringRun)
class ClusteringRunAdmin(admin.ModelAdmin):
    """Admin for ClusteringRun model."""
    list_display = [
        'id', 'client_name', 'project_id', 'service_id',
        'clustering_method', 'status', 'optimal_clusters', 'created_at'
    ]
    list_filter = ['status', 'clustering_method', 'created_at']
    search_fields = ['id', 'client_name', 'project_id', 'service_id']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'optimal_clusters',
        'calinski_harabasz_index', 'davies_bouldin_index',
        'input_tokens', 'output_tokens', 'total_tokens',
        'elapsed_time', 'price'
    ]
    fieldsets = (
        ('Identification', {
            'fields': ('id', 'client', 'user', 'client_name', 'project_id', 'service_id')
        }),
        ('Configuration', {
            'fields': ('clustering_method', 'embedding_model', 'generate_descriptions')
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Results', {
            'fields': ('optimal_clusters', 'calinski_harabasz_index', 'davies_bouldin_index')
        }),
        ('Usage', {
            'fields': ('input_tokens', 'output_tokens', 'total_tokens', 'media_duration', 'price'),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': ('elapsed_time', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [ClusterResultInline, ClusterFileInline]


@admin.register(ClusterResult)
class ClusterResultAdmin(admin.ModelAdmin):
    """Admin for ClusterResult model."""
    list_display = ['id', 'run', 'cluster_id', 'cluster_label', 'file_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['cluster_label', 'description']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['run']


@admin.register(ClusterFile)
class ClusterFileAdmin(admin.ModelAdmin):
    """Admin for ClusterFile model."""
    list_display = ['id', 'run', 'filename', 'cluster_id', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['filename', 'filepath']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['run', 'original_file', 'cluster_result']


@admin.register(ClusterStorage)
class ClusterStorageAdmin(admin.ModelAdmin):
    """Admin for ClusterStorage model."""
    list_display = ['id', 'run', 'upload_storage_location', 'created_at']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['run']

