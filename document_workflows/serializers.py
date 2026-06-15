from rest_framework import serializers
from document_workflows.models import Workflow, WorkflowStep, WorkflowAssignment, WorkflowRun, WorkflowAuditLog


class WorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workflow
        fields = [
            "id",
            "name",
            "description",
            "project_id",
            "service_id",
            "client_name",
            "status",
            "created_at",
            "updated_at",
        ]


class WorkflowStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowStep
        fields = [
            "id",
            "workflow",
            "step_number",
            "name",
            "assignee_role",
            "step_type",
            "status",
            "sla_hours",
            "escalation_user",
            "approval_required",
            "notify_on_completion",
            "created_at",
            "updated_at",
        ]


class WorkflowAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowAssignment
        fields = [
            "id",
            "workflow",
            "step",
            "assigned_to",
            "status",
            "comments",
            "sla_deadline",
            "escalated",
            "escalated_at",
            "escalated_to",
            "escalation_note",
            "created_at",
            "updated_at",
        ]


class WorkflowRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowRun
        fields = [
            "id",
            "workflow",
            "project_id",
            "service_id",
            "client_name",
            "status",
            "file",
            "current_step",
            "sla_deadline",
            "created_at",
            "updated_at",
            "error_message",
        ]


class WorkflowAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowAuditLog
        fields = [
            "id",
            "run",
            "step",
            "action",
            "actor",
            "details",
            "timestamp",
        ]
