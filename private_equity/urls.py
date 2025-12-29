from django.urls import path
from .views import (
    DueDiligenceRunListCreateView,
    DueDiligenceRunDetailView,
    DocumentClassificationView,
    RiskClauseExtractionView,
    FindingsReportView,
    RiskClauseSummaryView,
    DocumentTypeSummaryView,
    ServiceExecutionListCreateView,
    ServiceOutputListCreateView,
    # PE Value Metrics Views
    ClosingChecklistListCreateView,
    ClosingChecklistDetailView,
    PostCloseObligationListCreateView,
    DealVelocityMetricsListView,
    ClauseLibraryListCreateView,
    DealVelocityAnalyticsView,
    ChecklistProgressView,
)

app_name = 'private_equity'

urlpatterns = [
    # Due Diligence Run Management (also aliased as deal-workspaces for frontend compatibility)
    path('due-diligence-runs/', DueDiligenceRunListCreateView.as_view(), name='dd-runs-list-create'),
    path('due-diligence-runs/<int:pk>/', DueDiligenceRunDetailView.as_view(), name='dd-run-detail'),
    # Alias endpoints for frontend compatibility (deal-workspaces = due-diligence-runs)
    path('deal-workspaces/', DueDiligenceRunListCreateView.as_view(), name='deal-workspaces-list-create'),
    path('deal-workspaces/<int:pk>/', DueDiligenceRunDetailView.as_view(), name='deal-workspace-detail'),

    # Document Classification
    path('classify-documents/', DocumentClassificationView.as_view(), name='classify-documents'),

    # Risk Clause Extraction
    path('extract-risk-clauses/', RiskClauseExtractionView.as_view(), name='extract-risk-clauses'),

    # Findings Reports
    path('findings-reports/', FindingsReportView.as_view(), name='findings-reports'),

    # Analytics and Summaries
    path('risk-clause-summary/', RiskClauseSummaryView.as_view(), name='risk-clause-summary'),
    path('document-type-summary/', DocumentTypeSummaryView.as_view(), name='document-type-summary'),

    # Service Execution & Output Tracking
    path('service-executions/', ServiceExecutionListCreateView.as_view(), name='service-executions'),
    path('service-outputs/', ServiceOutputListCreateView.as_view(), name='service-outputs'),

    # ═══════════════════════════════════════════════════════════════
    # 💼 PE VALUE METRICS ENDPOINTS
    # ═══════════════════════════════════════════════════════════════

    # Closing Checklist
    path('closing-checklists/', ClosingChecklistListCreateView.as_view(), name='closing-checklists'),
    path('closing-checklists/<int:pk>/', ClosingChecklistDetailView.as_view(), name='closing-checklist-detail'),

    # Post-Close Obligations
    path('post-close-obligations/', PostCloseObligationListCreateView.as_view(), name='post-close-obligations'),

    # Deal Velocity Metrics
    path('deal-velocity-metrics/', DealVelocityMetricsListView.as_view(), name='deal-velocity-metrics'),
    path('deal-velocity-analytics/', DealVelocityAnalyticsView.as_view(), name='deal-velocity-analytics'),

    # Clause Library
    path('clause-library/', ClauseLibraryListCreateView.as_view(), name='clause-library'),

    # Progress Analytics
    path('checklist-progress/', ChecklistProgressView.as_view(), name='checklist-progress'),
]
