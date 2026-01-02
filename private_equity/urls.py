from django.urls import path
from .views import (
    DueDiligenceRunListCreateView,
    DueDiligenceRunDetailView,
    DocumentClassificationView,
    RiskClauseExtractionView,
    IssueSpottingView,
    FindingsReportView,
    SyncDataRoomView,
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
    # Panel Management & RFP Views
    PanelFirmListCreateView,
    RFPListCreateView,
    BidAnalysisView,
    EngagementLetterListCreateView,
    # Signature Tracking Views
    SignatureTrackerListCreateView,
    # Closing Management Views
    ConditionPrecedentListCreateView,
    ClosingBinderListCreateView,
    # Compliance Tracking Views
    CovenantListCreateView,
    ConsentFilingListCreateView,
    PortfolioComplianceView,
    RiskHeatmapView,
    # Task Status View
    PETaskStatusView,
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

    # AI Issue Spotting
    path('issue-spotting/', IssueSpottingView.as_view(), name='issue-spotting'),

    # Findings Reports
    path('findings-reports/', FindingsReportView.as_view(), name='findings-reports'),

    # Data Room Sync
    path('sync-data-room/', SyncDataRoomView.as_view(), name='sync-data-room'),

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

    # ═══════════════════════════════════════════════════════════════
    # 🏢 PANEL MANAGEMENT & RFP ENDPOINTS
    # ═══════════════════════════════════════════════════════════════

    # Panel Firms
    path('panel-firms/', PanelFirmListCreateView.as_view(), name='panel-firms'),

    # RFPs
    path('rfps/', RFPListCreateView.as_view(), name='rfps'),

    # Bid Analysis
    path('bid-analysis/', BidAnalysisView.as_view(), name='bid-analysis'),

    # Engagement Letters
    path('engagement-letters/', EngagementLetterListCreateView.as_view(), name='engagement-letters'),

    # ═══════════════════════════════════════════════════════════════
    # ✍️ SIGNATURE TRACKING ENDPOINTS
    # ═══════════════════════════════════════════════════════════════

    # Signature Trackers
    path('signature-trackers/', SignatureTrackerListCreateView.as_view(), name='signature-trackers'),

    # ═══════════════════════════════════════════════════════════════
    # 📋 CLOSING MANAGEMENT ENDPOINTS
    # ═══════════════════════════════════════════════════════════════

    # Conditions Precedent
    path('conditions-precedent/', ConditionPrecedentListCreateView.as_view(), name='conditions-precedent'),

    # Closing Binders
    path('closing-binders/', ClosingBinderListCreateView.as_view(), name='closing-binders'),

    # ═══════════════════════════════════════════════════════════════
    # 📊 COMPLIANCE TRACKING ENDPOINTS
    # ═══════════════════════════════════════════════════════════════

    # Covenants
    path('covenants/', CovenantListCreateView.as_view(), name='covenants'),

    # Consent Filings
    path('consent-filings/', ConsentFilingListCreateView.as_view(), name='consent-filings'),

    # Portfolio Compliance Dashboard
    path('portfolio-compliance/', PortfolioComplianceView.as_view(), name='portfolio-compliance'),

    # Risk Heatmap
    path('risk-heatmap/', RiskHeatmapView.as_view(), name='risk-heatmap'),

    # ═══════════════════════════════════════════════════════════════
    # 📊 TASK STATUS ENDPOINT
    # ═══════════════════════════════════════════════════════════════

    # Task Status (similar to TranslationTaskStatusView)
    path('task-status/', PETaskStatusView.as_view(), name='task-status'),
]
