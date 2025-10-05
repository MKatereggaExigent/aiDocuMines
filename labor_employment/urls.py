from django.urls import path
from .views import (
    WorkplaceCommunicationsRunListCreateView,
    WorkplaceCommunicationsRunDetailView,
    CommunicationAnalysisView,
    WageHourAnalysisView,
    PolicyComparisonView,
    EEOCPacketView,
    CommunicationPatternView,
    ComplianceAlertView,
    MessageAnalysisSummaryView,
    ComplianceAlertSummaryView,
    WageHourSummaryView,
    ServiceExecutionListCreateView,
    ServiceOutputListCreateView,
)

app_name = 'labor_employment'

urlpatterns = [
    # Workplace Communications Run Management
    path('communications-runs/', WorkplaceCommunicationsRunListCreateView.as_view(), name='comm-runs-list-create'),
    path('communications-runs/<int:pk>/', WorkplaceCommunicationsRunDetailView.as_view(), name='comm-run-detail'),
    
    # Communication Analysis
    path('analyze-communications/', CommunicationAnalysisView.as_view(), name='analyze-communications'),
    
    # Wage Hour Analysis
    path('wage-hour-analysis/', WageHourAnalysisView.as_view(), name='wage-hour-analysis'),
    
    # Policy Comparison
    path('policy-comparison/', PolicyComparisonView.as_view(), name='policy-comparison'),
    
    # EEOC Packet Generation
    path('eeoc-packets/', EEOCPacketView.as_view(), name='eeoc-packets'),
    
    # Communication Pattern Detection
    path('communication-patterns/', CommunicationPatternView.as_view(), name='communication-patterns'),
    
    # Compliance Alerts
    path('compliance-alerts/', ComplianceAlertView.as_view(), name='compliance-alerts'),
    path('compliance-alerts/<int:pk>/', ComplianceAlertView.as_view(), name='compliance-alert-detail'),
    
    # Analytics and Summaries
    path('message-analysis-summary/', MessageAnalysisSummaryView.as_view(), name='message-analysis-summary'),
    path('compliance-alert-summary/', ComplianceAlertSummaryView.as_view(), name='compliance-alert-summary'),
    path('wage-hour-summary/', WageHourSummaryView.as_view(), name='wage-hour-summary'),

    # Service Execution Management
    path('service-executions/', ServiceExecutionListCreateView.as_view(), name='service-executions'),
    path('service-outputs/', ServiceOutputListCreateView.as_view(), name='service-outputs'),
]
