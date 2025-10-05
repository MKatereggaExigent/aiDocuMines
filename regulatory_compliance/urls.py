from django.urls import path
from .views import (
    ComplianceRunListCreateView, ComplianceRunDetailView,
    RegulatoryRequirementView, RequirementAnalysisView,
    PolicyMappingView, DSARRequestView, DSARRequestDetailView,
    RedactionTaskView, ComplianceAlertView,
    ComplianceSummaryView, DSARSummaryView, RedactionSummaryView,
    AlertSummaryView, ComplianceReportView,
    ServiceExecutionListCreateView, ServiceOutputListCreateView
)

app_name = 'regulatory_compliance'

urlpatterns = [
    # Compliance Run Management
    path('runs/', ComplianceRunListCreateView.as_view(), name='compliance-runs'),
    path('runs/<int:pk>/', ComplianceRunDetailView.as_view(), name='compliance-run-detail'),
    
    # Regulatory Requirements
    path('requirements/', RegulatoryRequirementView.as_view(), name='regulatory-requirements'),
    path('requirements/analyze/', RequirementAnalysisView.as_view(), name='requirement-analysis'),
    
    # Policy Mapping
    path('policy-mappings/', PolicyMappingView.as_view(), name='policy-mappings'),
    
    # Data Subject Access Requests (DSAR)
    path('dsar-requests/', DSARRequestView.as_view(), name='dsar-requests'),
    path('dsar-requests/<int:pk>/', DSARRequestDetailView.as_view(), name='dsar-request-detail'),
    
    # Document Redaction
    path('redaction-tasks/', RedactionTaskView.as_view(), name='redaction-tasks'),
    
    # Compliance Alerts
    path('alerts/', ComplianceAlertView.as_view(), name='compliance-alerts'),
    path('alerts/<int:pk>/', ComplianceAlertView.as_view(), name='compliance-alert-detail'),
    
    # Analytics and Reporting
    path('analytics/compliance-summary/', ComplianceSummaryView.as_view(), name='compliance-summary'),
    path('analytics/dsar-summary/', DSARSummaryView.as_view(), name='dsar-summary'),
    path('analytics/redaction-summary/', RedactionSummaryView.as_view(), name='redaction-summary'),
    path('analytics/alert-summary/', AlertSummaryView.as_view(), name='alert-summary'),
    
    # Report Generation
    path('reports/generate/', ComplianceReportView.as_view(), name='generate-compliance-report'),

    # Service Execution Management
    path('service-executions/', ServiceExecutionListCreateView.as_view(), name='service-executions'),
    path('service-outputs/', ServiceOutputListCreateView.as_view(), name='service-outputs'),
]
