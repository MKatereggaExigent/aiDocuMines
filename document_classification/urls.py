"""
Document Classification URL Configuration

URL routing for document clustering/classification API endpoints.
"""

from django.urls import path
from document_classification.views import (
    health_check,
    SubmitClusteringAPIView,
    ClusteringStatusAPIView,
    ClusteringResultsAPIView,
    ClusteringRunListAPIView,
    ClusterDetailsAPIView,
)

app_name = 'document_classification'

urlpatterns = [
    # Health check
    path('health/', health_check, name='health_check'),
    
    # Clustering endpoints
    path('submit/', SubmitClusteringAPIView.as_view(), name='submit_clustering'),
    path('status/', ClusteringStatusAPIView.as_view(), name='clustering_status'),
    path('results/', ClusteringResultsAPIView.as_view(), name='clustering_results'),
    path('runs/', ClusteringRunListAPIView.as_view(), name='clustering_runs'),
    path('cluster/', ClusterDetailsAPIView.as_view(), name='cluster_details'),
]

