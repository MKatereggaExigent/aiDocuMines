# document_structures/tasks.py

from celery import shared_task
from document_structures import utils, models
from core.models import File, Run, User
from django.db import transaction


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_document_partition_task(
    self,
    document_structure_run_id: str,
    store_embeddings: bool = True
):
    """
    Background task that performs partitioning and extraction on a single document.
    """

    try:
        # Look up the DocumentStructureRun object
        ds_run = models.DocumentStructureRun.objects.get(id=document_structure_run_id)
        ds_run.status = "Processing"
        ds_run.save()

        # Get references to linked objects
        file = ds_run.file
        run = ds_run.run
        user = ds_run.user

        # Run partitioning
        utils.process_document_structures(
            file=file,
            run=run,
            user=user,
            partition_strategy=ds_run.partition_strategy,
            store_embeddings=store_embeddings,
        )

        ds_run.status = "Completed"
        ds_run.error_message = None
        ds_run.save()

    except Exception as e:
        ds_run.status = "Failed"
        ds_run.error_message = str(e)
        ds_run.save()
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_document_comparison_task(
    self,
    comparison_id: str,
):
    """
    Background task to compare two document structure runs
    """

    try:
        comparison = models.DocumentComparison.objects.get(id=comparison_id)
        comparison.status = "Processing"
        comparison.save()

        run1 = comparison.run_1
        run2 = comparison.run_2

        # Run the comparison
        result = utils.compare_document_runs(run1, run2)

        comparison.lexical_similarity = result.lexical_similarity
        comparison.semantic_similarity = result.semantic_similarity
        comparison.deviation_report = result.deviation_report or {}
        comparison.status = "Completed"
        comparison.save()

    except Exception as e:
        comparison.status = "Failed"
        comparison.save()
        raise

