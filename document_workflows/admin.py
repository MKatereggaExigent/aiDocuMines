from django.contrib import admin
from document_workflows.models import Workflow, WorkflowStep, WorkflowAssignment, WorkflowRun, WorkflowAuditLog


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'project_id', 'service_id', 'client_name', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'project_id', 'client_name')


@admin.register(WorkflowStep)
class WorkflowStepAdmin(admin.ModelAdmin):
    list_display = ('name', 'workflow', 'step_number', 'step_type', 'status', 'sla_hours', 'approval_required')
    list_filter = ('step_type', 'status')
    ordering = ('workflow', 'step_number')


@admin.register(WorkflowAssignment)
class WorkflowAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'workflow', 'step', 'assigned_to', 'status', 'sla_deadline', 'escalated')
    list_filter = ('status', 'escalated')


@admin.register(WorkflowRun)
class WorkflowRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'workflow', 'status', 'client_name', 'sla_deadline', 'created_at')
    list_filter = ('status',)


@admin.register(WorkflowAuditLog)
class WorkflowAuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'step', 'action', 'actor', 'timestamp')
    list_filter = ('action', 'actor')
    search_fields = ('run__id', 'actor', 'action')
    ordering = ('-timestamp',)
