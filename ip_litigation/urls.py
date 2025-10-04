from django.urls import path
from .views import (
    PatentAnalysisRunListCreateView,
    PatentAnalysisRunDetailView,
    PatentDocumentView,
    PatentClaimView,
    PriorArtDocumentView,
    ClaimChartView,
    ClaimChartDetailView,
    InfringementAnalysisView,
    ValidityChallengeView,
    PatentAnalysisSummaryView,
    ClaimChartSummaryView,
    InfringementSummaryView,
    ValiditySummaryView,
)

app_name = 'ip_litigation'

urlpatterns = [
    # Patent Analysis Run Management
    path('analysis-runs/', PatentAnalysisRunListCreateView.as_view(), name='analysis-runs-list-create'),
    path('analysis-runs/<int:pk>/', PatentAnalysisRunDetailView.as_view(), name='analysis-run-detail'),
    
    # Patent Document Management
    path('patent-documents/', PatentDocumentView.as_view(), name='patent-documents'),
    
    # Patent Claim Analysis
    path('patent-claims/', PatentClaimView.as_view(), name='patent-claims'),
    
    # Prior Art Management
    path('prior-art-documents/', PriorArtDocumentView.as_view(), name='prior-art-documents'),
    
    # Claim Chart Management
    path('claim-charts/', ClaimChartView.as_view(), name='claim-charts'),
    path('claim-charts/<int:pk>/', ClaimChartDetailView.as_view(), name='claim-chart-detail'),
    
    # Infringement Analysis
    path('infringement-analyses/', InfringementAnalysisView.as_view(), name='infringement-analyses'),
    
    # Validity Challenges
    path('validity-challenges/', ValidityChallengeView.as_view(), name='validity-challenges'),
    
    # Analytics and Summaries
    path('patent-analysis-summary/', PatentAnalysisSummaryView.as_view(), name='patent-analysis-summary'),
    path('claim-chart-summary/', ClaimChartSummaryView.as_view(), name='claim-chart-summary'),
    path('infringement-summary/', InfringementSummaryView.as_view(), name='infringement-summary'),
    path('validity-summary/', ValiditySummaryView.as_view(), name='validity-summary'),
]
