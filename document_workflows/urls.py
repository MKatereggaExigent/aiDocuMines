from django.urls import path
from .views import (
    WorkflowListCreateAPIView,
    WorkflowDetailAPIView,
    WorkflowStepListAPIView,
    WorkflowAssignmentListAPIView,
    SubmitWorkflowRunAPIView,
    CheckWorkflowStatusAPIView,
    ApproveStepAPIView,
    WorkflowAuditLogListView,
    WorkflowRunSLAUpdateView,
    AddCommentToStepView,
    health_check,
)

urlpatterns = [
    path("workflows/", WorkflowListCreateAPIView.as_view(), name="workflow-list-create"),
    path("workflows/<uuid:pk>/", WorkflowDetailAPIView.as_view(), name="workflow-detail"),
    path("workflow-steps/", WorkflowStepListAPIView.as_view(), name="workflow-step-list"),
    path("workflow-assignments/", WorkflowAssignmentListAPIView.as_view(), name="workflow-assignment-list"),
    path("submit-workflow-run/", SubmitWorkflowRunAPIView.as_view(), name="submit-workflow-run"),
    path("check-workflow-status/", CheckWorkflowStatusAPIView.as_view(), name="check-workflow-status"),
    path("approve-step/", ApproveStepAPIView.as_view(), name="approve-step"),
    path("audit-logs/", WorkflowAuditLogListView.as_view(), name="workflow-audit-logs"),
    path("run-sla/", WorkflowRunSLAUpdateView.as_view(), name="workflow-run-sla"),
    path("add-comment/", AddCommentToStepView.as_view(), name="workflow-add-comment"),
    path("health/", health_check, name="health_check"),
]
