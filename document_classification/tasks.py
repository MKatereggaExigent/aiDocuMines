"""
Document Classification Celery Tasks

Async tasks for document clustering/classification.
"""

import logging
from celery import shared_task
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def cluster_documents_task(
    self,
    run_id: str,
    file_ids: List[int],
    clustering_method: str = 'agglomerative',
    nb_cluster_method: str = 'silhouette',
    embedding_model: str = 'bert-base-uncased',
    generate_descriptions: bool = True
) -> Dict[str, Any]:
    """
    Celery task to cluster documents asynchronously.

    Args:
        run_id: UUID of the ClusteringRun
        file_ids: List of File IDs to cluster
        clustering_method: Clustering algorithm to use
        nb_cluster_method: Method to determine optimal cluster count
        embedding_model: Embedding model to use
        generate_descriptions: Whether to generate AI descriptions

    Returns:
        Dictionary with clustering results
    """
    from document_classification.models import ClusteringRun
    from document_classification.utils.config import ClusteringConfig
    from document_classification.utils.flow_handler import ClusteringFlowHandler

    try:
        logger.info(f"Starting clustering task for run {run_id}")

        # Get the run
        run = ClusteringRun.objects.get(id=run_id)

        # Create config
        config = ClusteringConfig(
            clustering_method=clustering_method,
            nb_cluster_method=nb_cluster_method,
            embedding_model=embedding_model,
            generate_descriptions=generate_descriptions
        )

        # Process clustering
        handler = ClusteringFlowHandler(run, config)
        results = handler.process(file_ids)

        logger.info(f"Clustering completed for run {run_id}: {results.get('status')}")

        return {
            'run_id': str(run_id),
            'status': results.get('status'),
            'optimal_clusters': results.get('optimal_clusters', 0),
            'file_count': len(file_ids)
        }

    except ClusteringRun.DoesNotExist:
        logger.error(f"ClusteringRun {run_id} not found")
        return {'run_id': str(run_id), 'status': 'Failed', 'error': 'Run not found'}

    except Exception as e:
        logger.error(f"Clustering task failed for run {run_id}: {e}")

        # Update run status
        try:
            run = ClusteringRun.objects.get(id=run_id)
            run.status = 'Failed'
            run.error_message = str(e)
            run.save()
        except Exception:
            pass

        # Retry on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        return {'run_id': str(run_id), 'status': 'Failed', 'error': str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def subcluster_documents_task(
    self,
    sub_run_id: str,
    run_id: str,
    cluster_id: int,
    clustering_method: str = 'agglomerative',
    nb_cluster_method: str = 'silhouette'
) -> Dict[str, Any]:
    """
    Celery task to sub-cluster documents within an existing cluster.

    Args:
        sub_run_id: UUID of the SubClusterRun
        run_id: UUID of the parent ClusteringRun
        cluster_id: Parent cluster ID to sub-cluster
        clustering_method: Clustering algorithm to use
        nb_cluster_method: Method to determine optimal cluster count

    Returns:
        Dictionary with sub-clustering results
    """
    from document_classification.models import ClusteringRun, SubClusterRun, ClusterFile
    from document_classification.utils.config import ClusteringConfig
    from document_classification.utils.executor import ClusteringExecutor

    try:
        logger.info(f"Starting sub-clustering task for sub_run {sub_run_id}, "
                    f"cluster {cluster_id} in run {run_id}")

        parent_run = ClusteringRun.objects.get(id=run_id)
        sub_run = SubClusterRun.objects.get(id=sub_run_id)

        sub_run.status = 'Processing'
        sub_run.save()

        # Get files in this cluster
        cluster_files = ClusterFile.objects.filter(
            run=parent_run, cluster_id=cluster_id, status='Completed'
        )
        if cluster_files.count() < 2:
            raise ValueError(
                f"At least 2 files required for sub-clustering, "
                f"got {cluster_files.count()}"
            )

        filepaths = [cf.filepath for cf in cluster_files]
        filenames = [cf.filename for cf in cluster_files]
        texts = [cf.extracted_text for cf in cluster_files if cf.extracted_text]

        if len(texts) < 2:
            raise ValueError(
                f"At least 2 files with extracted text required, got {len(texts)}"
            )

        config = ClusteringConfig(
            clustering_method=clustering_method,
            nb_cluster_method=nb_cluster_method
        )
        executor = ClusteringExecutor(config)
        results = executor.execute_subcluster(
            filepaths=filepaths,
            filenames=filenames,
            run_id=str(run_id),
            parent_cluster_id=cluster_id,
            texts=texts
        )

        sub_run.status = results.get('status', 'Failed')
        sub_run.optimal_subclusters = results.get('optimal_subclusters', 0)
        sub_run.result_data = results
        sub_run.save()

        logger.info(f"Sub-clustering completed for sub_run {sub_run_id}: "
                    f"{results.get('status')}")

        return {
            'sub_run_id': str(sub_run_id),
            'run_id': str(run_id),
            'status': results.get('status'),
            'optimal_subclusters': results.get('optimal_subclusters', 0)
        }

    except (ClusteringRun.DoesNotExist, SubClusterRun.DoesNotExist) as e:
        logger.error(f"Run not found: {e}")
        return {'status': 'Failed', 'error': str(e)}

    except Exception as e:
        logger.error(f"Sub-clustering task failed for sub_run {sub_run_id}: {e}")
        try:
            sub_run = SubClusterRun.objects.get(id=sub_run_id)
            sub_run.status = 'Failed'
            sub_run.error_message = str(e)
            sub_run.save()
        except Exception:
            pass

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        return {'sub_run_id': str(sub_run_id), 'status': 'Failed', 'error': str(e)}


@shared_task
def cleanup_old_clustering_runs_task(days: int = 30) -> Dict[str, Any]:
    """
    Cleanup old clustering runs and their associated files.
    
    Args:
        days: Number of days to keep runs
        
    Returns:
        Dictionary with cleanup results
    """
    from datetime import timedelta
    from django.utils import timezone
    from document_classification.models import ClusteringRun
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    old_runs = ClusteringRun.objects.filter(created_at__lt=cutoff_date)
    count = old_runs.count()
    
    # Delete old runs (cascade will delete related records)
    old_runs.delete()
    
    logger.info(f"Cleaned up {count} old clustering runs")
    
    return {'deleted_runs': count}


@shared_task
def recompute_cluster_descriptions_task(run_id: str) -> Dict[str, Any]:
    """
    Recompute AI descriptions for an existing clustering run.
    
    Args:
        run_id: UUID of the ClusteringRun
        
    Returns:
        Dictionary with results
    """
    from document_classification.models import ClusteringRun, ClusterResult, ClusterFile
    from document_classification.utils.function_utils import generate_cluster_descriptions
    
    try:
        run = ClusteringRun.objects.get(id=run_id)
        
        # Get texts grouped by cluster
        cluster_texts = {}
        for cluster_result in run.cluster_results.all():
            texts = []
            for cluster_file in cluster_result.files.all():
                if cluster_file.extracted_text:
                    texts.append(cluster_file.extracted_text)
            if texts:
                cluster_texts[cluster_result.cluster_id] = texts
        
        # Generate new descriptions
        descriptions = generate_cluster_descriptions(cluster_texts)
        
        # Update cluster results
        for cluster_result in run.cluster_results.all():
            desc = descriptions.get(cluster_result.cluster_id, {})
            cluster_result.cluster_label = desc.get('label', cluster_result.cluster_label)
            cluster_result.description = desc.get('description', '')
            cluster_result.keywords = desc.get('keywords', [])
            cluster_result.save()
        
        return {'run_id': str(run_id), 'status': 'Completed', 'clusters_updated': len(descriptions)}
        
    except ClusteringRun.DoesNotExist:
        return {'run_id': str(run_id), 'status': 'Failed', 'error': 'Run not found'}
    except Exception as e:
        logger.error(f"Failed to recompute descriptions for run {run_id}: {e}")
        return {'run_id': str(run_id), 'status': 'Failed', 'error': str(e)}

