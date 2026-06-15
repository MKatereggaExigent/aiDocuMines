"""
Clustering Executor

Orchestrates the document clustering pipeline.
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from document_classification.utils.config import ClusteringConfig
from document_classification.utils.file_extractor import FileExtractor
from document_classification.utils.function_utils import (
    generate_embeddings,
    perform_clustering,
    generate_cluster_descriptions,
    calculate_clustering_metrics
)

logger = logging.getLogger(__name__)


class ClusteringExecutor:
    """
    Executes the document clustering pipeline.
    """
    
    def __init__(self, config: Optional[ClusteringConfig] = None):
        """
        Initialize the executor.
        
        Args:
            config: Clustering configuration
        """
        self.config = config or ClusteringConfig()
        self.file_extractor = FileExtractor()
        self.elapsed_time = {}
        self.token_usage = {'input': 0, 'output': 0, 'total': 0}
    
    def execute(
        self,
        filepaths: List[str],
        filenames: List[str],
        run_id: str,
        cluster_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Execute the clustering pipeline.
        
        Args:
            filepaths: List of file paths to cluster
            filenames: List of file names
            run_id: Unique run identifier
            cluster_ids: Optional pre-assigned cluster IDs (for sub-clustering)
            
        Returns:
            Dictionary with clustering results
        """
        start_time = time.time()
        results = {
            'run_id': run_id,
            'status': 'Processing',
            'files': [],
            'clusters': [],
            'metrics': {},
            'elapsed_time': {},
            'token_usage': {}
        }
        
        try:
            # Step 1: Extract text from files
            extraction_start = time.time()
            texts, file_results = self._extract_texts(filepaths, filenames)
            results['files'] = file_results
            self.elapsed_time['extraction'] = time.time() - extraction_start
            
            if len(texts) < 2:
                raise ValueError("At least 2 valid files are required for clustering")
            
            # Step 2: Generate embeddings
            embedding_start = time.time()
            embeddings = generate_embeddings(
                texts,
                model_name=self.config.embedding_model,
                batch_size=self.config.batch_size
            )
            self.elapsed_time['embedding'] = time.time() - embedding_start
            
            # Step 3: Perform clustering
            clustering_start = time.time()
            labels, optimal_clusters = perform_clustering(
                embeddings,
                method=self.config.clustering_method,
                nb_cluster_method=self.config.nb_cluster_method,
                distance_threshold=self.config.distance_threshold,
                eps=self.config.dbscan_eps,
                min_samples=self.config.dbscan_min_samples,
                n_clusters=self.config.kmeans_n_clusters or self.config.spectral_n_clusters
            )
            self.elapsed_time['clustering'] = time.time() - clustering_start
            
            # If cluster_ids provided (sub-clustering), assign those instead of computed labels
            if cluster_ids:
                for i, file_result in enumerate(results['files']):
                    if file_result['status'] == 'Completed':
                        file_result['cluster_id'] = cluster_ids[i]
            
            # Step 4: Calculate metrics
            metrics = calculate_clustering_metrics(embeddings, labels)
            results['metrics'] = metrics
            
            # Step 5: Assign clusters to files
            valid_idx = 0
            for file_result in results['files']:
                if file_result['status'] == 'Completed':
                    file_result['cluster_id'] = int(labels[valid_idx])
                    valid_idx += 1
            
            # Step 6: Generate cluster descriptions
            if self.config.generate_descriptions:
                description_start = time.time()
                cluster_texts = self._group_texts_by_cluster(texts, labels)
                descriptions = generate_cluster_descriptions(
                    cluster_texts,
                    api_key=self.config.llm_api_key,
                    model=self.config.llm_model
                )
                self.elapsed_time['description'] = time.time() - description_start
            else:
                descriptions = {i: {'label': f'Cluster {i}', 'description': '', 'keywords': []}
                               for i in range(optimal_clusters)}
            
            # Build cluster results
            for cluster_id in range(optimal_clusters):
                cluster_files = [f for f in results['files'] 
                               if f.get('cluster_id') == cluster_id]
                desc = descriptions.get(cluster_id, {})
                results['clusters'].append({
                    'cluster_id': cluster_id,
                    'label': desc.get('label', f'Cluster {cluster_id}'),
                    'description': desc.get('description', ''),
                    'keywords': desc.get('keywords', []),
                    'file_count': len(cluster_files),
                    'files': [f['filename'] for f in cluster_files]
                })
            
            results['optimal_clusters'] = optimal_clusters
            results['status'] = 'Completed'
            
        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            results['status'] = 'Failed'
            results['error'] = str(e)
        
        self.elapsed_time['total'] = time.time() - start_time
        results['elapsed_time'] = self.elapsed_time
        results['token_usage'] = self.token_usage
        
        # Save results
        self._save_results(results, run_id)
        
        return results
    
    def execute_subcluster(
        self,
        filepaths: List[str],
        filenames: List[str],
        run_id: str,
        parent_cluster_id: int,
        texts: List[str]
    ) -> Dict[str, Any]:
        """
        Execute sub-clustering on files within an existing cluster.

        Args:
            filepaths: List of file paths to sub-cluster
            filenames: List of file names
            run_id: Unique run identifier
            parent_cluster_id: The parent cluster ID being sub-clustered
            texts: Pre-extracted text content

        Returns:
            Dictionary with sub-clustering results
        """
        start_time = time.time()
        results = {
            'run_id': run_id,
            'status': 'Processing',
            'files': [],
            'subclusters': [],
            'parent_cluster_id': parent_cluster_id,
            'metrics': {},
            'elapsed_time': {},
            'token_usage': {}
        }

        try:
            if len(texts) < 2:
                raise ValueError("At least 2 files are required for sub-clustering")

            # Generate embeddings
            embedding_start = time.time()
            embeddings = generate_embeddings(
                texts,
                model_name=self.config.embedding_model,
                batch_size=self.config.batch_size
            )
            self.elapsed_time['embedding'] = time.time() - embedding_start

            # Perform sub-clustering
            clustering_start = time.time()
            labels, optimal_clusters = perform_clustering(
                embeddings,
                method=self.config.clustering_method,
                nb_cluster_method=self.config.nb_cluster_method,
                distance_threshold=self.config.distance_threshold,
                eps=self.config.dbscan_eps,
                min_samples=2,
                n_clusters=self.config.kmeans_n_clusters
            )
            self.elapsed_time['clustering'] = time.time() - clustering_start

            # Assign sub-cluster IDs (prefixed to avoid collision with parent)
            for i, (filepath, filename) in enumerate(zip(filepaths, filenames)):
                results['files'].append({
                    'filepath': filepath,
                    'filename': filename,
                    'status': 'Completed',
                    'subcluster_id': int(labels[i]),
                    'parent_cluster_id': parent_cluster_id
                })

            # Calculate metrics
            metrics = calculate_clustering_metrics(embeddings, labels)
            results['metrics'] = metrics

            # Group into sub-clusters
            subcluster_texts = self._group_texts_by_cluster(texts, labels)
            for sub_id, sub_texts in subcluster_texts.items():
                results['subclusters'].append({
                    'subcluster_id': int(sub_id),
                    'parent_cluster_id': parent_cluster_id,
                    'file_count': len(sub_texts),
                    'files': [f for f in results['files']
                              if f.get('subcluster_id') == sub_id]
                })

            results['optimal_subclusters'] = optimal_clusters
            results['status'] = 'Completed'

        except Exception as e:
            logger.error(f"Sub-clustering failed: {e}")
            results['status'] = 'Failed'
            results['error'] = str(e)

        self.elapsed_time['total'] = time.time() - start_time
        results['elapsed_time'] = self.elapsed_time

        return results

    def _extract_texts(
        self,
        filepaths: List[str],
        filenames: List[str]
    ) -> tuple:
        """Extract text from all files."""
        texts = []
        file_results = []

        for filepath, filename in zip(filepaths, filenames):
            result = {
                'filepath': filepath,
                'filename': filename,
                'status': 'Processing',
                'error': None,
                'cluster_id': None
            }

            if not self.config.is_supported_file(filename):
                result['status'] = 'Unsupported'
                result['error'] = 'Unsupported file type'
                file_results.append(result)
                continue

            text, error = self.file_extractor.extract(filepath)

            if error:
                result['status'] = 'Failed'
                result['error'] = error
            elif not text or len(text.strip()) < 10:
                result['status'] = 'Failed'
                result['error'] = 'No text content extracted'
            else:
                result['status'] = 'Completed'
                result['text'] = text
                texts.append(text)

            file_results.append(result)

        return texts, file_results

    def _group_texts_by_cluster(
        self,
        texts: List[str],
        labels
    ) -> Dict[int, List[str]]:
        """Group texts by their cluster labels."""
        cluster_texts = {}
        for text, label in zip(texts, labels):
            label = int(label)
            if label not in cluster_texts:
                cluster_texts[label] = []
            cluster_texts[label].append(text)
        return cluster_texts

    def _save_results(self, results: Dict[str, Any], run_id: str):
        """Save results to storage."""
        try:
            storage_path = self.config.get_storage_path(run_id, self.config.results_subdir)
            results_file = os.path.join(storage_path, 'results.json')

            # Remove text content before saving (too large)
            save_results = results.copy()
            for f in save_results.get('files', []):
                f.pop('text', None)

            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(save_results, f, indent=2, default=str)

            logger.info(f"Results saved to {results_file}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")

