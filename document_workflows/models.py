from django.db import models
from core.models import File
import uuid


class Workflow(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('Archived', 'Archived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    project_id = models.CharField(max_length=255, db_index=True)
    service_id = models.CharField(max_length=255, db_index=True)
    client_name = models.CharField(max_length=255, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Workflow {self.name} - {self.status}"


class WorkflowStep(models.Model):
    STEP_TYPE_CHOICES = [
        ('Review', 'Review'),
        ('Approval', 'Approval'),
        ('Processing', 'Processing'),
        ('Notification', 'Notification'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('InProgress', 'InProgress'),
        ('Completed', 'Completed'),
        ('Skipped', 'Skipped'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="steps")
    step_number = models.IntegerField(db_index=True)
    name = models.CharField(max_length=255)
    assignee_role = models.CharField(max_length=255)
    step_type = models.CharField(max_length=20, choices=STEP_TYPE_CHOICES, default='Review', db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', db_index=True)
    sla_hours = models.IntegerField(blank=True, null=True)
    escalation_user = models.CharField(max_length=255, blank=True, null=True)
    approval_required = models.BooleanField(default=False)
    notify_on_completion = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['step_number']

    def __str__(self):
        return f"Step {self.step_number}: {self.name} ({self.step_type})"


class WorkflowAssignment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('InReview', 'InReview'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="assignments")
    step = models.ForeignKey(WorkflowStep, on_delete=models.CASCADE, related_name="assignments")
    assigned_to = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', db_index=True)
    comments = models.TextField(blank=True, null=True)
    sla_deadline = models.DateTimeField(blank=True, null=True)
    escalated = models.BooleanField(default=False)
    escalated_at = models.DateTimeField(blank=True, null=True)
    escalated_to = models.CharField(max_length=255, blank=True, null=True)
    escalation_note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Assignment {self.id} - {self.assigned_to} ({self.status})"


class WorkflowRun(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('InProgress', 'InProgress'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="runs")
    project_id = models.CharField(max_length=255, db_index=True)
    service_id = models.CharField(max_length=255, db_index=True)
    client_name = models.CharField(max_length=255, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', db_index=True)
    file = models.ForeignKey(File, on_delete=models.SET_NULL, null=True, blank=True, related_name="workflow_runs")
    current_step = models.ForeignKey(WorkflowStep, on_delete=models.SET_NULL, null=True, blank=True, related_name="running_runs")
    sla_deadline = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"WorkflowRun {self.id} - {self.status}"


class WorkflowAuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(WorkflowRun, on_delete=models.CASCADE, related_name="audit_logs")
    step = models.ForeignKey(WorkflowStep, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50)
    actor = models.CharField(max_length=255)
    details = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"AuditLog {self.id} - {self.action} on {self.run_id}"
