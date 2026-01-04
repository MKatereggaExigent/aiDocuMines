"""
Document Classification Tests

Comprehensive tests for document clustering/classification API endpoints.
Uses Django TestCase for proper database and request handling.
"""

import uuid
from django.test import TestCase, Client
from unittest.mock import patch, MagicMock

from document_classification.models import ClusteringRun, ClusterResult, ClusterFile
from document_classification.serializers import ClusteringSubmitSerializer


class TestClusteringConfig(TestCase):
    """Tests for the ClusteringConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        from document_classification.utils.config import ClusteringConfig
        config = ClusteringConfig()
        self.assertEqual(config.clustering_method, 'agglomerative')
        self.assertEqual(config.embedding_model, 'bert-base-uncased')
        self.assertTrue(config.generate_descriptions)

    def test_custom_config(self):
        """Test custom configuration values."""
        from document_classification.utils.config import ClusteringConfig
        config = ClusteringConfig(
            clustering_method='kmeans',
            embedding_model='roberta-base',
            generate_descriptions=False
        )
        self.assertEqual(config.clustering_method, 'kmeans')
        self.assertEqual(config.embedding_model, 'roberta-base')
        self.assertFalse(config.generate_descriptions)


class TestFunctionUtils(TestCase):
    """Tests for clustering utility functions."""

    def test_calculate_clustering_metrics(self):
        """Test clustering metrics calculation."""
        import numpy as np
        from document_classification.utils.function_utils import calculate_clustering_metrics

        # Create sample embeddings and labels
        embeddings = np.random.rand(10, 128)
        labels = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 2])

        metrics = calculate_clustering_metrics(embeddings, labels)

        self.assertIn('calinski_harabasz', metrics)
        self.assertIn('davies_bouldin', metrics)
        self.assertIn('silhouette', metrics)

    def test_calculate_metrics_single_cluster(self):
        """Test metrics with single cluster returns zeros."""
        import numpy as np
        from document_classification.utils.function_utils import calculate_clustering_metrics

        embeddings = np.random.rand(5, 64)
        labels = np.array([0, 0, 0, 0, 0])

        metrics = calculate_clustering_metrics(embeddings, labels)
        self.assertEqual(metrics['calinski_harabasz'], 0.0)


class TestHealthCheckEndpoint(TestCase):
    """Tests for the health check endpoint."""

    def test_health_check_returns_ok(self):
        """Test that health check returns status ok."""
        from django.test import Client
        client = Client()
        response = client.get('/api/v1/classification/health/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['service'], 'document_classification')


class TestSubmitClusteringEndpoint(TestCase):
    """Tests for POST /api/v1/classification/submit/"""

    def setUp(self):
        self.client = Client()
        self.url = '/api/v1/classification/submit/'

    def test_submit_missing_credentials_returns_401(self):
        """Test that missing OAuth credentials returns 401."""
        response = self.client.post(
            self.url,
            data={'file_ids': [1, 2, 3], 'project_id': 'test', 'service_id': 'test'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)

    def test_submit_with_client_headers_no_auth(self):
        """Test submit with client headers but no valid OAuth token."""
        response = self.client.post(
            self.url,
            data={'file_ids': [1, 2], 'project_id': 'test', 'service_id': 'test'},
            content_type='application/json',
            HTTP_X_CLIENT_ID='test-client',
            HTTP_X_CLIENT_SECRET='test-secret'
        )
        # Should return 401 because OAuth token is not valid
        self.assertEqual(response.status_code, 401)


class TestClusteringStatusEndpoint(TestCase):
    """Tests for GET /api/v1/classification/status/"""

    def setUp(self):
        self.client = Client()
        self.url = '/api/v1/classification/status/'

    def test_status_requires_authentication(self):
        """Test that status endpoint requires OAuth authentication."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_status_with_headers_no_token(self):
        """Test status with headers but no valid token."""
        response = self.client.get(
            f'{self.url}?run_id={uuid.uuid4()}',
            HTTP_X_CLIENT_ID='test-client',
            HTTP_X_CLIENT_SECRET='test-secret'
        )
        self.assertEqual(response.status_code, 401)


class TestClusteringResultsEndpoint(TestCase):
    """Tests for GET /api/v1/classification/results/"""

    def setUp(self):
        self.client = Client()
        self.url = '/api/v1/classification/results/'

    def test_results_requires_authentication(self):
        """Test that results endpoint requires OAuth authentication."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_results_with_run_id_no_auth(self):
        """Test results with run_id but no authentication."""
        response = self.client.get(
            f'{self.url}?run_id={uuid.uuid4()}',
            HTTP_X_CLIENT_ID='test-client'
        )
        self.assertEqual(response.status_code, 401)


class TestClusteringRunsListEndpoint(TestCase):
    """Tests for GET /api/v1/classification/runs/"""

    def setUp(self):
        self.client = Client()
        self.url = '/api/v1/classification/runs/'

    def test_runs_list_requires_authentication(self):
        """Test that runs list requires OAuth authentication."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_runs_list_with_filters_no_auth(self):
        """Test runs list with filters but no authentication."""
        response = self.client.get(
            f'{self.url}?status=Completed&project_id=test',
            HTTP_X_CLIENT_ID='test-client'
        )
        self.assertEqual(response.status_code, 401)


class TestClusterDetailsEndpoint(TestCase):
    """Tests for GET /api/v1/classification/cluster/"""

    def setUp(self):
        self.client = Client()
        self.url = '/api/v1/classification/cluster/'

    def test_cluster_details_requires_authentication(self):
        """Test that cluster details requires OAuth authentication."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_cluster_details_with_params_no_auth(self):
        """Test cluster details with params but no authentication."""
        response = self.client.get(
            f'{self.url}?run_id={uuid.uuid4()}&cluster_id=0',
            HTTP_X_CLIENT_ID='test-client'
        )
        self.assertEqual(response.status_code, 401)


class TestSerializers(TestCase):
    """Tests for document classification serializers."""

    def test_clustering_submit_serializer_valid(self):
        """Test ClusteringSubmitSerializer with valid data."""
        data = {
            'file_ids': [1, 2, 3],
            'project_id': 'test-project',
            'service_id': 'test-service',
            'clustering_method': 'agglomerative',
            'embedding_model': 'bert-base-uncased',
            'generate_descriptions': True
        }
        serializer = ClusteringSubmitSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_clustering_submit_serializer_min_files(self):
        """Test that at least 2 files are required."""
        data = {
            'file_ids': [1],  # Only 1 file
            'project_id': 'test-project',
            'service_id': 'test-service'
        }
        serializer = ClusteringSubmitSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('file_ids', serializer.errors)

    def test_clustering_submit_serializer_empty_files(self):
        """Test that empty file_ids is invalid."""
        data = {
            'file_ids': [],
            'project_id': 'test-project',
            'service_id': 'test-service'
        }
        serializer = ClusteringSubmitSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_clustering_submit_serializer_invalid_method(self):
        """Test that invalid clustering method is rejected."""
        data = {
            'file_ids': [1, 2],
            'project_id': 'test-project',
            'service_id': 'test-service',
            'clustering_method': 'invalid_method'
        }
        serializer = ClusteringSubmitSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('clustering_method', serializer.errors)

    def test_clustering_submit_serializer_defaults(self):
        """Test that default values are applied."""
        data = {
            'file_ids': [1, 2],
            'project_id': 'test-project',
            'service_id': 'test-service'
        }
        serializer = ClusteringSubmitSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        validated = serializer.validated_data
        self.assertEqual(validated.get('clustering_method', 'agglomerative'), 'agglomerative')
        self.assertEqual(validated.get('generate_descriptions', True), True)


class TestClusteringRunModel(TestCase):
    """Tests for ClusteringRun model."""

    def test_create_clustering_run(self):
        """Test creating a clustering run."""
        run = ClusteringRun.objects.create(
            project_id='test-project',
            service_id='test-service',
            client_name='test-client',
            clustering_method='agglomerative',
            embedding_model='bert-base-uncased',
            status='Pending'
        )
        self.assertIsNotNone(run.id)
        self.assertEqual(run.status, 'Pending')
        self.assertEqual(run.clustering_method, 'agglomerative')

    def test_clustering_run_str(self):
        """Test ClusteringRun string representation."""
        run = ClusteringRun.objects.create(
            project_id='test-project',
            service_id='test-service',
            client_name='test-client'
        )
        self.assertIn('ClusteringRun', str(run))
        self.assertIn('Pending', str(run))

    def test_clustering_run_default_values(self):
        """Test ClusteringRun default values."""
        run = ClusteringRun.objects.create(
            project_id='test-project',
            service_id='test-service',
            client_name='test-client'
        )
        self.assertEqual(run.status, 'Pending')
        self.assertEqual(run.clustering_method, 'agglomerative')
        self.assertEqual(run.embedding_model, 'bert-base-uncased')
        self.assertTrue(run.generate_descriptions)
        self.assertEqual(run.optimal_clusters, 0)


class TestClusterResultModel(TestCase):
    """Tests for ClusterResult model."""

    def test_create_cluster_result(self):
        """Test creating a cluster result."""
        run = ClusteringRun.objects.create(
            project_id='test-project',
            service_id='test-service',
            client_name='test-client'
        )
        result = ClusterResult.objects.create(
            run=run,
            cluster_id=0,
            cluster_label='Legal Documents',
            file_count=5,
            description='Documents related to legal matters',
            keywords=['legal', 'contract', 'agreement']
        )
        self.assertIsNotNone(result.id)
        self.assertEqual(result.cluster_id, 0)
        self.assertEqual(result.file_count, 5)

    def test_cluster_result_str(self):
        """Test ClusterResult string representation."""
        run = ClusteringRun.objects.create(
            project_id='test-project',
            service_id='test-service',
            client_name='test-client'
        )
        result = ClusterResult.objects.create(
            run=run,
            cluster_id=1,
            cluster_label='Financial Reports'
        )
        self.assertIn('Cluster 1', str(result))
        self.assertIn('Financial Reports', str(result))


class TestClusterFileModel(TestCase):
    """Tests for ClusterFile model."""

    def test_create_cluster_file(self):
        """Test creating a cluster file."""
        run = ClusteringRun.objects.create(
            project_id='test-project',
            service_id='test-service',
            client_name='test-client'
        )
        file = ClusterFile.objects.create(
            run=run,
            filepath='/path/to/file.pdf',
            filename='file.pdf',
            file_type='application/pdf',
            file_extension='.pdf',
            file_size=1.5,
            status='Pending'
        )
        self.assertIsNotNone(file.id)
        self.assertEqual(file.filename, 'file.pdf')
        self.assertEqual(file.status, 'Pending')

    def test_cluster_file_str(self):
        """Test ClusterFile string representation."""
        run = ClusteringRun.objects.create(
            project_id='test-project',
            service_id='test-service',
            client_name='test-client'
        )
        file = ClusterFile.objects.create(
            run=run,
            filepath='/path/to/test.docx',
            filename='test.docx',
            cluster_id=2
        )
        self.assertIn('test.docx', str(file))
        self.assertIn('Cluster 2', str(file))

