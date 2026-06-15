import logging
from celery import shared_task
from django.shortcuts import get_object_or_404
from document_workflows.models import WorkflowRun, WorkflowStep
from document_workflows.utils import get_next_step, check_sla_breach, log_audit

logger = logging.getLogger(__name__)


@shared_task
def execute_workflow_run_task(run_id):
    logger.info(f"Starting workflow run execution for run_id={run_id}")

    workflow_run = get_object_or_404(WorkflowRun, id=run_id)
    actor = workflow_run.client_name or 'system'

    try:
        log_audit(workflow_run, 'submitted', actor)

        workflow_run.status = "InProgress"
        workflow_run.save()

        current_step = workflow_run.current_step
        if not current_step:
            first_step = WorkflowStep.objects.filter(workflow=workflow_run.workflow).order_by('step_number').first()
            if not first_step:
                workflow_run.status = "Failed"
                workflow_run.error_message = "No steps defined for workflow"
                workflow_run.save()
                log_audit(workflow_run, 'failed', actor, details={'error': 'No steps defined for workflow'})
                return {"error": "No steps defined for workflow", "run_id": run_id}
            workflow_run.current_step = first_step
            first_step.status = "InProgress"
            first_step.save()
            workflow_run.save()
            current_step = first_step

        current_step_number = current_step.step_number

        next_step = get_next_step(workflow_run.workflow_id, current_step_number)
        if next_step:
            current_step.status = "Completed"
            current_step.save()
            log_audit(workflow_run, 'completed', actor, step=current_step)
            workflow_run.current_step = next_step
            next_step.status = "InProgress"
            next_step.save()
            workflow_run.status = "InProgress"
            workflow_run.save()
            log_audit(workflow_run, 'submitted', actor, step=next_step)

            if next_step.notify_on_completion:
                send_workflow_notification.delay(
                    run_id=str(workflow_run.id),
                    step_id=str(next_step.id),
                    notification_type='step_completed',
                )
        else:
            current_step.status = "Completed"
            current_step.save()
            log_audit(workflow_run, 'completed', actor, step=current_step)
            workflow_run.current_step = None
            workflow_run.status = "Completed"
            workflow_run.save()
            log_audit(workflow_run, 'completed', actor)

        logger.info(f"Workflow run {run_id} completed successfully")
        return {"run_id": run_id, "status": workflow_run.status}

    except Exception as e:
        logger.error(f"Workflow run {run_id} failed: {e}")
        workflow_run.status = "Failed"
        workflow_run.error_message = str(e)
        workflow_run.save()
        log_audit(workflow_run, 'failed', actor, details={'error': str(e)})
        return {"error": str(e), "run_id": run_id}


@shared_task
def monitor_sla_breaches():
    logger.info("Checking SLA breaches across all active workflow runs")
    active_runs = WorkflowRun.objects.filter(status__in=('Pending', 'InProgress'))
    breached_count = 0
    for run in active_runs:
        try:
            if check_sla_breach(run):
                breached_count += 1
        except Exception as e:
            logger.error(f"Error checking SLA for run {run.id}: {e}")
    logger.info(f"SLA check complete. {breached_count} assignments escalated.")
    return {"checked_runs": active_runs.count(), "escalated": breached_count}


@shared_task
def send_workflow_notification(run_id, step_id, notification_type):
    logger.info(f"Notification placeholder: run={run_id}, step={step_id}, type={notification_type}")
    return {"status": "notification_placeholder", "run_id": run_id, "type": notification_type}
