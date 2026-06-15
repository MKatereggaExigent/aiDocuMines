import logging
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import get_object_or_404
from document_workflows.models import WorkflowRun, WorkflowStep, WorkflowAssignment, WorkflowAuditLog

logger = logging.getLogger(__name__)


def calculate_sla_deadline(step):
    if step.sla_hours:
        return timezone.now() + timedelta(hours=step.sla_hours)
    return None


def check_sla_breach(run):
    if run.status not in ('InProgress', 'Pending'):
        return False
    assignments = WorkflowAssignment.objects.filter(
        workflow=run.workflow,
        status__in=('Pending', 'InReview'),
        sla_deadline__isnull=False,
        sla_deadline__lt=timezone.now(),
        escalated=False,
    )
    breached = False
    for assignment in assignments:
        escalate_assignment(assignment)
        breached = True
    return breached


def escalate_assignment(assignment):
    assignment.escalated = True
    assignment.escalated_at = timezone.now()
    assignment_status = assignment.status

    if assignment.step and assignment.step.escalation_user:
        assignment.escalated_to = assignment.step.escalation_user
    else:
        assignment.escalated_to = assignment.assigned_to

    assignment.escalation_note = "Auto-escalated due to SLA breach"
    assignment.save()

    log_audit(
        run=WorkflowRun.objects.filter(workflow=assignment.workflow).first(),
        action='escalated',
        actor='system',
        step=assignment.step,
        details={
            'assignment_id': str(assignment.id),
            'escalated_to': assignment.escalated_to,
            'previous_status': assignment_status,
        }
    )


def log_audit(run, action, actor, step=None, details=None):
    if not run:
        logger.warning(f"Cannot log audit: no run provided for action {action}")
        return None
    log_entry = WorkflowAuditLog.objects.create(
        run=run,
        step=step,
        action=action,
        actor=actor,
        details=details or {},
    )
    return log_entry


def can_approve(user_role, assignment):
    if not assignment.step:
        return False
    if assignment.step.assignee_role == user_role:
        return True
    if assignment.step.approval_required and user_role == assignment.step.assignee_role:
        return True
    return False


def get_next_step(workflow_id, current_step_number):
    steps = WorkflowStep.objects.filter(workflow_id=workflow_id, step_number__gt=current_step_number).order_by('step_number')
    return steps.first() if steps.exists() else None


def advance_workflow(run_id):
    run = get_object_or_404(WorkflowRun, id=run_id)
    current_step = run.current_step
    current_step_number = current_step.step_number if current_step else 0

    actor = run.client_name if run.client_name else 'system'

    if current_step:
        current_step.status = 'Completed'
        current_step.save()
        log_audit(run, 'completed', actor, step=current_step)

    next_step = get_next_step(run.workflow_id, current_step_number)

    if next_step:
        run.current_step = next_step
        next_step.status = 'InProgress'
        next_step.save()
        run.status = 'InProgress'

        if next_step.sla_hours:
            run.sla_deadline = calculate_sla_deadline(next_step)

        log_audit(run, 'submitted', actor, step=next_step)
    else:
        run.status = 'Completed'
        run.current_step = None
        log_audit(run, 'completed', actor)

    run.save()
    return run


def process_workflow_step(run_id, step_id):
    run = get_object_or_404(WorkflowRun, id=run_id)
    step = get_object_or_404(WorkflowStep, id=step_id)

    logger.info(f"Processing step {step.step_number} ({step.name}) for run {run_id}")

    step.status = 'InProgress'
    step.save()
    run.current_step = step
    run.status = 'InProgress'
    run.save()

    log_audit(run, 'submitted', run.client_name or 'system', step=step)

    if step.step_type in ('Review', 'Approval'):
        sla_deadline = calculate_sla_deadline(step)
        assignment = WorkflowAssignment.objects.create(
            workflow=run.workflow,
            step=step,
            assigned_to=step.assignee_role,
            status='Pending',
            sla_deadline=sla_deadline,
        )
        if sla_deadline and not run.sla_deadline:
            run.sla_deadline = sla_deadline
            run.save()
        log_audit(run, 'created', run.client_name or 'system', step=step, details={
            'assignment_id': str(assignment.id),
            'assigned_to': step.assignee_role,
        })

    return {"run_id": str(run_id), "step_id": str(step_id), "status": "InProgress"}
