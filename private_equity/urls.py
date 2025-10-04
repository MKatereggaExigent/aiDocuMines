from django.urls import path
from .views import (
    DueDiligenceRunListCreateView,
    DueDiligenceRunDetailView,
    DocumentClassificationView,
    RiskClauseExtractionView,
    FindingsReportView,
    RiskClauseSummaryView,
    DocumentTypeSummaryView,
)

app_name = 'private_equity'

urlpatterns = [
    # Due Diligence Run Management
    path('due-diligence-runs/', DueDiligenceRunListCreateView.as_view(), name='dd-runs-list-create'),
    path('due-diligence-runs/<int:pk>/', DueDiligenceRunDetailView.as_view(), name='dd-run-detail'),
    
    # Document Classification
    path('classify-documents/', DocumentClassificationView.as_view(), name='classify-documents'),
    
    # Risk Clause Extraction
    path('extract-risk-clauses/', RiskClauseExtractionView.as_view(), name='extract-risk-clauses'),
    
    # Findings Reports
    path('findings-reports/', FindingsReportView.as_view(), name='findings-reports'),
    
    # Analytics and Summaries
    path('risk-clause-summary/', RiskClauseSummaryView.as_view(), name='risk-clause-summary'),
    path('document-type-summary/', DocumentTypeSummaryView.as_view(), name='document-type-summary'),
]
