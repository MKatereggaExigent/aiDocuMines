"""
Flow Handler

Handles the document classification workflow with database integration.
"""

import logging
from typing import List, Dict, Any, Optional
from django.db import transaction

from document_classification.models import ClusteringRun, ClusterResult, ClusterFile
from document_classification.utils.config import ClusteringConfig
from document_classification.utils.executor import ClusteringExecutor
from core.models import File

logger = logging.getLogger(__name__)


class ClusteringFlowHandler:
    """
    Handles the complete clustering workflow with database persistence.
    """
    
    def __init__(self, run: ClusteringRun, config: Optional[ClusteringConfig] = None):
        """
        Initialize the flow handler.
        
        Args:
            run: ClusteringRun model instance
            config: Optional clustering configuration
        """
        self.run = run
        self.config = config or ClusteringConfig(
            clustering_method=run.clustering_method,
            embedding_model=run.embedding_model,
            generate_descriptions=run.generate_descriptions
        )
        self.executor = ClusteringExecutor(self.config)
    
    def process(self, file_ids: List[int]) -> Dict[str, Any]:
        """
        Process the clustering workflow.
        
        Args:
            file_ids: List of File IDs to cluster
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Update run status
            self.run.status = 'Processing'
            self.run.save()
            
            # Get files from database
            files = File.objects.filter(id__in=file_ids)
            if files.count() < 2:
                raise ValueError("At least 2 files are required for clustering")
            
            # Create ClusterFile records
            filepaths = []
            filenames = []
            cluster_files = []
            
            for file_obj in files:
                cluster_file = ClusterFile.objects.create(
                    run=self.run,
                    original_file=file_obj,
                    filepath=file_obj.filepath,
                    filename=file_obj.filename,
                    file_type=file_obj.file_type,
                    file_extension=file_obj.file_extension,
                    file_size=file_obj.file_size or 0,
                    status='Pending'
                )
                cluster_files.append(cluster_file)
                filepaths.append(file_obj.filepath)
                filenames.append(file_obj.filename)
            
            # Execute clustering
            results = self.executor.execute(
                filepaths=filepaths,
                filenames=filenames,
                run_id=str(self.run.id)
            )
            
            # Update database with results
            self._update_database(results, cluster_files)
            
            return results
            
        except Exception as e:
            logger.error(f"Clustering flow failed: {e}")
            self.run.status = 'Failed'
            self.run.error_message = str(e)
            self.run.save()
            raise
    
    @transaction.atomic
    def _update_database(self, results: Dict[str, Any], cluster_files: List[ClusterFile]):
        """Update database with clustering results."""
        
        # Update run with metrics
        self.run.status = results.get('status', 'Failed')
        self.run.optimal_clusters = results.get('optimal_clusters', 0)
        self.run.calinski_harabasz_index = results.get('metrics', {}).get('calinski_harabasz', 0)
        self.run.davies_bouldin_index = results.get('metrics', {}).get('davies_bouldin', 0)
        self.run.elapsed_time = results.get('elapsed_time', {})
        
        if results.get('error'):
            self.run.error_message = results['error']
        
        self.run.save()
        
        # Create ClusterResult records
        cluster_results = {}
        for cluster_data in results.get('clusters', []):
            cluster_result = ClusterResult.objects.create(
                run=self.run,
                cluster_id=cluster_data['cluster_id'],
                cluster_label=cluster_data.get('label'),
                description=cluster_data.get('description'),
                keywords=cluster_data.get('keywords', []),
                file_count=cluster_data.get('file_count', 0)
            )
            cluster_results[cluster_data['cluster_id']] = cluster_result
        
        # Update ClusterFile records
        file_results = {f['filename']: f for f in results.get('files', [])}
        
        for cluster_file in cluster_files:
            file_result = file_results.get(cluster_file.filename, {})
            cluster_file.status = file_result.get('status', 'Failed')
            cluster_file.error_message = file_result.get('error')
            cluster_file.cluster_id = file_result.get('cluster_id')
            
            # Link to ClusterResult
            if cluster_file.cluster_id is not None:
                cluster_file.cluster_result = cluster_results.get(cluster_file.cluster_id)
            
            cluster_file.save()
        
        logger.info(f"Database updated for run {self.run.id}")

