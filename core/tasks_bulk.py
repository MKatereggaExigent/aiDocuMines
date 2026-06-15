import json
import logging
import os
from datetime import datetime
from typing import List, Optional

from celery import shared_task, group, chain, chord
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from core.models import BulkJob, BulkJobFileResult, File, Run, Storage
from core.bulk_registry import get_bulk_handler

logger = logging.getLogger(__name__)

BATCH_CHUNK_SIZE = 50


def get_service_display_name(job_type: str) -> str:
    """Look up display_name from the service catalog."""
    from core.service_catalog import ALL_SERVICES
    for svc in ALL_SERVICES:
        if svc["service_type"] == job_type:
            return svc.get("display_name", job_type)
    return job_type


def get_bulk_output_folder(job: BulkJob):
    """Get or create .batch-output/<service_display_name>/ under the input folder.

    Returns the output Folder or None if job has no folder_id.
    """
    from document_operations.models import Folder

    if not job.folder_id:
        logger.warning(f"BulkJob {job.id} has no folder_id — cannot create output folder")
        return None

    svc_display = get_service_display_name(job.job_type)

    try:
        input_folder = Folder.objects.get(id=job.folder_id)
    except Folder.DoesNotExist:
        logger.warning(f"Input folder {job.folder_id} not found for job {job.id}")
        return None

    batch_root, _ = Folder.objects.get_or_create(
        name=".batch-output",
        parent=input_folder,
        user=job.user,
        project_id=job.project_id,
        service_id=job.service_id,
        defaults={"is_trashed": False},
    )

    output_folder, _ = Folder.objects.get_or_create(
        name=svc_display,
        parent=batch_root,
        user=job.user,
        project_id=job.project_id,
        service_id=job.service_id,
        defaults={"is_trashed": False},
    )

    return output_folder


def create_bulk_output_file(file_id: int, job: BulkJob, result_data: dict) -> Optional[int]:
    """Create a File record for the bulk-processed result and link it to the output folder.

    Returns the output File id, or None on failure.
    """
    from document_operations.models import FileFolderLink
    from django.contrib.contenttypes.models import ContentType

    try:
        input_file = File.objects.get(id=file_id)
    except File.DoesNotExist:
        logger.error(f"Input file {file_id} not found for bulk job {job.id}")
        return None

    output_folder = get_bulk_output_folder(job)
    if not output_folder:
        logger.warning(f"No output folder available for bulk job {job.id}")
        return None

    # Create Run for this output artifact
    run = Run.objects.create(
        user=job.user,
        status="Completed",
    )

    # Create Storage linked to the Run
    storage = Storage.objects.create(
        user=job.user,
        content_type=ContentType.objects.get_for_model(Run),
        object_id=run.run_id,
        output_storage_location=None,
    )

    # Derive output filename from input file
    base_name, ext = os.path.splitext(input_file.filename)
    output_filename = f"{base_name}_{job.job_type}_result.json"

    # Build a meaningful filepath
    output_dir = os.path.join(
        os.path.dirname(input_file.filepath) if input_file.filepath else "",
        ".batch-output",
        output_folder.name,
    )
    output_filepath = os.path.join(output_dir, output_filename)

    output_file = File.objects.create(
        filename=output_filename,
        filepath=output_filepath,
        file_size=len(json.dumps(result_data, default=str)),
        file_type="application/json",
        extension="json",
        md5_hash=None,
        origin_file=input_file,
        status="Completed",
        run=run,
        content=json.dumps(result_data, indent=2, default=str),
        user=job.user,
        project_id=job.project_id,
        service_id=job.service_id,
        storage=storage,
    )

    FileFolderLink.objects.create(
        file=output_file,
        folder=output_folder,
    )

    logger.info(
        f"Created bulk output file {output_file.id} -> "
        f"folder {output_folder.id} ({output_folder.name})"
    )
    return output_file.id


@shared_task(bind=True)
def process_batch_all_files_in_bulk(self, file_ids: List[int], user_id: int,
                                     job_id: str, job_type: str,
                                     project_id: str = None,
                                     service_id: str = None, **kwargs):
    """Handle a batch_all task: dispatches all file_ids to the handler in one call."""
    handler = get_bulk_handler(job_type)
    if not handler:
        logger.error(f"No handler for job_type={job_type}")
        return {"error": f"No handler for {job_type}"}

    logger.info(f"process_batch_all_files_in_bulk: job={job_id}, "
                f"handler={job_type}, files={len(file_ids)}")
    try:
        result = handler.call_batch(file_ids, user_id, project_id=project_id,
                                    service_id=service_id, **kwargs)
        # Mark all files as Completed
        with transaction.atomic():
            BulkJobFileResult.objects.filter(bulk_job_id=job_id).update(
                status="Completed",
                result_data={"task_id": result.id if result else None},
                completed_at=timezone.now(),
            )
            BulkJob.objects.filter(id=job_id).update(
                processed_files=len(file_ids),
            )
        return {"status": "completed", "task_id": result.id if result else None,
                "file_count": len(file_ids)}
    except Exception as exc:
        logger.exception(f"Batch-all handler failed for job {job_id}")
        with transaction.atomic():
            BulkJobFileResult.objects.filter(bulk_job_id=job_id).update(
                status="Failed",
                error_message=str(exc),
                completed_at=timezone.now(),
            )
            BulkJob.objects.filter(id=job_id).update(
                failed_files=len(file_ids),
            )
        return {"error": str(exc), "file_count": len(file_ids)}


@shared_task(bind=True)
def process_single_file_in_bulk(self, file_id: int, user_id: int, job_id: str,
                                 job_type: str, project_id: str = None,
                                 service_id: str = None, **kwargs):
    handler = get_bulk_handler(job_type)
    if not handler:
        logger.error(f"No handler for job_type={job_type}")
        return {"error": f"No handler for {job_type}", "file_id": file_id}

    try:
        result = handler.call(file_id, user_id, project_id=project_id,
                              service_id=service_id, **kwargs)
        result_data = {"status": "completed", "task_id": result.id if result else None}

        with transaction.atomic():
            BulkJobFileResult.objects.update_or_create(
                bulk_job_id=job_id,
                file_id=file_id,
                defaults={
                    "status": "Completed",
                    "result_data": result_data,
                    "completed_at": timezone.now(),
                    "task_id": result.id if result else None,
                }
            )
            BulkJob.objects.filter(id=job_id).update(
                processed_files=F("processed_files") + 1
            )

        # Best-effort: create output file record + folder link
        try:
            job = BulkJob.objects.get(id=job_id)
            output_file_id = create_bulk_output_file(file_id, job, result_data)
            if output_file_id:
                result_data["output_file_id"] = output_file_id
                BulkJobFileResult.objects.filter(
                    bulk_job_id=job_id, file_id=file_id
                ).update(result_data=result_data)
        except Exception as exc:
            logger.warning(
                f"Failed to create output file for bulk {job_id} file {file_id}: {exc}"
            )

        return result_data

    except Exception as exc:
        logger.exception(f"Failed to process file {file_id} for bulk job {job_id}")
        with transaction.atomic():
            BulkJobFileResult.objects.update_or_create(
                bulk_job_id=job_id,
                file_id=file_id,
                defaults={
                    "status": "Failed",
                    "error_message": str(exc),
                    "completed_at": timezone.now(),
                }
            )
            BulkJob.objects.filter(id=job_id).update(
                failed_files=F("failed_files") + 1
            )
        return {"error": str(exc), "file_id": file_id}


@shared_task(bind=True)
def execute_bulk_job(self, job_id: str):
    try:
        job = BulkJob.objects.get(id=job_id)
    except BulkJob.DoesNotExist:
        logger.error(f"BulkJob {job_id} not found")
        return {"error": "Job not found"}

    job.status = "Processing"
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    handler = get_bulk_handler(job.job_type)
    if not handler:
        job.status = "Failed"
        job.save(update_fields=["status"])
        return {"error": f"No handler for {job.job_type}"}

    # Pre-create the output folder tree so all per-file tasks land in the same place
    if job.folder_id:
        try:
            get_bulk_output_folder(job)
        except Exception as exc:
            logger.warning(f"Failed to pre-create output folder for job {job_id}: {exc}")

    file_ids = list(
        BulkJobFileResult.objects.filter(bulk_job=job, status="Pending")
        .values_list("file_id", flat=True)
    )

    if not file_ids:
        job.status = "Completed"
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "completed_at"])
        return {"message": "No files to process", "job_id": job_id}

    # batch_all handlers get ALL file_ids in a single task
    if handler.batch_all:
        logger.info(f"Batch-all handler {job.job_type}: dispatching single task "
                    f"with {len(file_ids)} files")
        task = process_batch_all_files_in_bulk.s(
            file_ids=file_ids,
            user_id=job.user_id,
            job_id=job_id,
            job_type=job.job_type,
            project_id=job.project_id,
            service_id=job.service_id,
            **(job.input_parameters or {}),
        )
        callback = finalize_bulk_job.s(str(job.id))
        result = chord([task])(callback)
        job.celery_group_id = result.id
        job.save(update_fields=["celery_group_id"])
        return {
            "job_id": job_id,
            "status": "Processing",
            "total_files": len(file_ids),
            "chunks": 1,
            "group_id": result.id,
            "mode": "batch_all",
        }

    tasks = []
    for file_id in file_ids:
        task = process_single_file_in_bulk.s(
            file_id=file_id,
            user_id=job.user_id,
            job_id=job_id,
            job_type=job.job_type,
            project_id=job.project_id,
            service_id=job.service_id,
            **(job.input_parameters or {}),
        )
        tasks.append(task)

    chunk_size = BATCH_CHUNK_SIZE
    chunks = [tasks[i:i + chunk_size] for i in range(0, len(tasks), chunk_size)]

    # Flatten chunks into a single group so chord can call finalize_bulk_job
    # when all file tasks complete
    all_tasks = []
    for chunk in chunks:
        all_tasks.extend(chunk)

    callback = finalize_bulk_job.s(str(job.id))
    result = chord(all_tasks)(callback)
    job.celery_group_id = result.id
    job.save(update_fields=["celery_group_id"])

    return {
        "job_id": job_id,
        "status": "Processing",
        "total_files": len(file_ids),
        "chunks": len(chunks),
        "group_id": result.id,
    }


@shared_task(bind=True)
def finalize_bulk_job(self, results, job_id: str):
    logger.info(f"finalize_bulk_job called for job {job_id} (received {len(results) if results else 0} results)")
    try:
        job = BulkJob.objects.get(id=job_id)
    except BulkJob.DoesNotExist:
        logger.error(f"finalize_bulk_job: job {job_id} not found")
        return {"error": "Job not found"}

    total = BulkJobFileResult.objects.filter(bulk_job=job).count()
    completed = BulkJobFileResult.objects.filter(bulk_job=job, status="Completed").count()
    failed = BulkJobFileResult.objects.filter(bulk_job=job, status="Failed").count()

    job.processed_files = completed
    job.failed_files = failed

    if failed == 0 and completed == total:
        job.status = "Completed"
    elif completed > 0 and failed > 0:
        job.status = "Partially_Completed"
    elif failed == total:
        job.status = "Failed"
    else:
        job.status = "Completed"

    job.completed_at = timezone.now()
    job.result_summary = {
        "total": total,
        "completed": completed,
        "failed": failed,
        "success_rate": round((completed / total * 100), 2) if total > 0 else 0,
    }
    job.save(update_fields=[
        "status", "processed_files", "failed_files",
        "completed_at", "result_summary",
    ])

    return {
        "job_id": job_id,
        "status": job.status,
        "total": total,
        "completed": completed,
        "failed": failed,
    }


@shared_task
def cancel_bulk_job(job_id: str):
    try:
        job = BulkJob.objects.get(id=job_id)
    except BulkJob.DoesNotExist:
        return {"error": "Job not found"}

    from celery.task.control import revoke

    if job.celery_group_id:
        try:
            revoke(job.celery_group_id, terminate=True, signal="SIGTERM")
        except Exception as exc:
            logger.warning(f"Failed to revoke group {job.celery_group_id}: {exc}")

    job.status = "Cancelled"
    job.save(update_fields=["status"])

    BulkJobFileResult.objects.filter(bulk_job=job, status="Pending").update(
        status="Skipped"
    )

    return {"job_id": job_id, "status": "Cancelled"}
