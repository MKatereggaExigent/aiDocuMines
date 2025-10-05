from django.urls import path
from .views import (
    MassClaimsRunListCreateView,
    MassClaimsRunDetailView,
    IntakeFormView,
    EvidenceDocumentView,
    PIIRedactionView,
    ExhibitPackageView,
    SettlementTrackingView,
    DuplicateDetectionView,
    EvidenceSummaryView,
    IntakeFormSummaryView,
    ServiceExecutionListCreateView,
    ServiceOutputListCreateView,
)

app_name = 'class_actions'

urlpatterns = [
    # Mass Claims Run Management
    path('mass-claims-runs/', MassClaimsRunListCreateView.as_view(), name='mc-runs-list-create'),
    path('mass-claims-runs/<int:pk>/', MassClaimsRunDetailView.as_view(), name='mc-run-detail'),
    
    # Intake Form Management
    path('intake-forms/', IntakeFormView.as_view(), name='intake-forms'),
    
    # Evidence Document Management
    path('evidence-documents/', EvidenceDocumentView.as_view(), name='evidence-documents'),
    
    # PII Redaction
    path('pii-redaction/', PIIRedactionView.as_view(), name='pii-redaction'),
    
    # Exhibit Package Management
    path('exhibit-packages/', ExhibitPackageView.as_view(), name='exhibit-packages'),
    
    # Settlement Tracking
    path('settlement-tracking/', SettlementTrackingView.as_view(), name='settlement-tracking'),
    
    # Duplicate Detection
    path('detect-duplicates/', DuplicateDetectionView.as_view(), name='detect-duplicates'),
    
    # Analytics and Summaries
    path('evidence-summary/', EvidenceSummaryView.as_view(), name='evidence-summary'),
    path('intake-form-summary/', IntakeFormSummaryView.as_view(), name='intake-form-summary'),

    # Service Execution Management
    path('service-executions/', ServiceExecutionListCreateView.as_view(), name='service-executions'),
    path('service-outputs/', ServiceOutputListCreateView.as_view(), name='service-outputs'),
]
