from celery import shared_task
from document_structures import utils, models
from core.models import File, Run, User
import traceback
import logging

logger = logging.getLogger("document_structures.tasks")


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
        ds_run = models.DocumentStructureRun.objects.get(id=document_structure_run_id)
        ds_run.status = "Processing"
        ds_run.save()

        file = ds_run.file
        run = ds_run.run
        user = ds_run.user

        utils.process_document_structures(
            file=file,
            run=run,
            user=user,
            partition_strategy=ds_run.partition_strategy,
            store_embeddings=store_embeddings,
            ds_run=ds_run,
        )

        ds_run.status = "Completed"
        ds_run.error_message = None
        ds_run.save()

    except Exception as e:
        logger.error(f"🔥 Error running partition task: {e}", exc_info=True)
        traceback.print_exc()
        ds_run.status = "Failed"
        ds_run.error_message = str(e)
        ds_run.save()
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_document_comparison_task(self, comparison_id: str):
    """
    Background task to compare two document structure runs.
    """

    try:
        comparison = models.DocumentComparison.objects.get(id=comparison_id)
        comparison.status = "Processing"
        comparison.save()

        run1 = comparison.run_1
        run2 = comparison.run_2

        # Call optimized utils function
        comparison_obj = utils.compare_document_runs(run1, run2)

        comparison.lexical_similarity = comparison_obj.lexical_similarity
        comparison.semantic_similarity = comparison_obj.semantic_similarity
        comparison.deviation_report = comparison_obj.deviation_report or {}
        comparison.status = "Completed"
        comparison.save()

        logger.warning(f"✅ Comparison {comparison.id} complete.")

    except Exception as e:
        logger.error(f"🔥 Error running comparison task: {e}", exc_info=True)
        comparison.status = "Failed"
        comparison.save()
        raise

