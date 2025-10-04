from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import get_object_or_404
from django.db.models import Avg, Count, Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from oauth2_provider.contrib.rest_framework import OAuth2Authentication, TokenHasReadWriteScope
from custom_authentication.permissions import IsClientOrAdmin
from .models import (
    PatentAnalysisRun, PatentDocument, PatentClaim, PriorArtDocument,
    ClaimChart, PatentLandscape, InfringementAnalysis, ValidityChallenge
)
from .serializers import (
    PatentAnalysisRunSerializer, PatentDocumentSerializer, PatentClaimSerializer,
    PriorArtDocumentSerializer, ClaimChartSerializer, PatentLandscapeSerializer,
    InfringementAnalysisSerializer, ValidityChallengeSerializer,
    PatentAnalysisSummarySerializer, ClaimChartSummarySerializer,
    InfringementSummarySerializer, ValiditySummarySerializer
)
from .tasks import (
    extract_patent_data_task, analyze_patent_claims_task, search_prior_art_task,
    generate_claim_chart_task, analyze_infringement_task, analyze_validity_task
)


class PatentAnalysisRunListCreateView(APIView):
    """
    List and create patent analysis runs for IP litigation.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    @swagger_auto_schema(
        operation_description="Get list of patent analysis runs",
        tags=["IP Litigation - Analysis Runs"],
        responses={200: PatentAnalysisRunSerializer(many=True)}
    )
    def get(self, request):
        """Get list of patent analysis runs for the user"""
        runs = PatentAnalysisRun.objects.filter(run__user=request.user)
        serializer = PatentAnalysisRunSerializer(runs, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Create a new patent analysis run",
        tags=["IP Litigation - Analysis Runs"],
        request_body=PatentAnalysisRunSerializer,
        responses={201: PatentAnalysisRunSerializer}
    )
    def post(self, request):
        """Create a new patent analysis run"""
        serializer = PatentAnalysisRunSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            analysis_run = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PatentAnalysisRunDetailView(APIView):
    """
    Retrieve, update, and delete patent analysis runs.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    @swagger_auto_schema(
        operation_description="Get patent analysis run details",
        tags=["IP Litigation - Analysis Runs"],
        responses={200: PatentAnalysisRunSerializer}
    )
    def get(self, request, pk):
        """Get patent analysis run details"""
        analysis_run = get_object_or_404(PatentAnalysisRun, pk=pk, run__user=request.user)
        serializer = PatentAnalysisRunSerializer(analysis_run)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Update patent analysis run",
        tags=["IP Litigation - Analysis Runs"],
        request_body=PatentAnalysisRunSerializer,
        responses={200: PatentAnalysisRunSerializer}
    )
    def put(self, request, pk):
        """Update patent analysis run"""
        analysis_run = get_object_or_404(PatentAnalysisRun, pk=pk, run__user=request.user)
        serializer = PatentAnalysisRunSerializer(analysis_run, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Delete patent analysis run",
        tags=["IP Litigation - Analysis Runs"],
        responses={204: "Patent analysis run deleted"}
    )
    def delete(self, request, pk):
        """Delete patent analysis run"""
        analysis_run = get_object_or_404(PatentAnalysisRun, pk=pk, run__user=request.user)
        analysis_run.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PatentDocumentView(APIView):
    """
    Manage patent documents for analysis.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    @swagger_auto_schema(
        operation_description="Get patent documents for an analysis run",
        tags=["IP Litigation - Patent Documents"],
        manual_parameters=[
            openapi.Parameter('analysis_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: PatentDocumentSerializer(many=True)}
    )
    def get(self, request):
        """Get patent documents for an analysis run"""
        analysis_run_id = request.query_params.get('analysis_run_id')
        if not analysis_run_id:
            return Response({"error": "analysis_run_id parameter is required"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure user owns the analysis run
        analysis_run = get_object_or_404(PatentAnalysisRun, pk=analysis_run_id, run__user=request.user)
        
        documents = PatentDocument.objects.filter(
            analysis_run=analysis_run,
            user=request.user
        )
        serializer = PatentDocumentSerializer(documents, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Add a patent document to analysis",
        tags=["IP Litigation - Patent Documents"],
        request_body=PatentDocumentSerializer,
        responses={201: PatentDocumentSerializer}
    )
    def post(self, request):
        """Add a patent document to analysis"""
        serializer = PatentDocumentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            document = serializer.save()
            
            # Trigger patent data extraction task
            extract_patent_data_task.delay(document.id, request.user.id)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PatentClaimView(APIView):
    """
    Manage patent claims extracted from patent documents.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    @swagger_auto_schema(
        operation_description="Get patent claims for a patent document",
        tags=["IP Litigation - Patent Claims"],
        manual_parameters=[
            openapi.Parameter('patent_document_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: PatentClaimSerializer(many=True)}
    )
    def get(self, request):
        """Get patent claims for a patent document"""
        patent_document_id = request.query_params.get('patent_document_id')
        if not patent_document_id:
            return Response({"error": "patent_document_id parameter is required"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure user owns the patent document
        patent_document = get_object_or_404(PatentDocument, pk=patent_document_id, user=request.user)
        
        claims = PatentClaim.objects.filter(
            patent_document=patent_document,
            user=request.user
        )
        serializer = PatentClaimSerializer(claims, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Trigger patent claim analysis",
        tags=["IP Litigation - Patent Claims"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'patent_document_id': openapi.Schema(type=openapi.TYPE_INTEGER)
            },
            required=['patent_document_id']
        ),
        responses={202: "Patent claim analysis started"}
    )
    def post(self, request):
        """Trigger patent claim analysis"""
        patent_document_id = request.data.get('patent_document_id')
        
        if not patent_document_id:
            return Response(
                {"error": "patent_document_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ensure user owns the patent document
        patent_document = get_object_or_404(PatentDocument, pk=patent_document_id, user=request.user)
        
        # Trigger claim analysis task
        task = analyze_patent_claims_task.delay(patent_document.id, request.user.id)
        
        return Response({
            "message": "Patent claim analysis started",
            "task_id": task.id,
            "patent_document_id": patent_document_id
        }, status=status.HTTP_202_ACCEPTED)


class PriorArtDocumentView(APIView):
    """
    Manage prior art documents for patent analysis.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    @swagger_auto_schema(
        operation_description="Get prior art documents for an analysis run",
        tags=["IP Litigation - Prior Art"],
        manual_parameters=[
            openapi.Parameter('analysis_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('document_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False)
        ],
        responses={200: PriorArtDocumentSerializer(many=True)}
    )
    def get(self, request):
        """Get prior art documents for an analysis run"""
        analysis_run_id = request.query_params.get('analysis_run_id')
        if not analysis_run_id:
            return Response({"error": "analysis_run_id parameter is required"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure user owns the analysis run
        analysis_run = get_object_or_404(PatentAnalysisRun, pk=analysis_run_id, run__user=request.user)
        
        documents = PriorArtDocument.objects.filter(
            analysis_run=analysis_run,
            user=request.user
        )
        
        # Apply document type filter
        document_type = request.query_params.get('document_type')
        if document_type:
            documents = documents.filter(document_type=document_type)
        
        serializer = PriorArtDocumentSerializer(documents, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Add a prior art document",
        tags=["IP Litigation - Prior Art"],
        request_body=PriorArtDocumentSerializer,
        responses={201: PriorArtDocumentSerializer}
    )
    def post(self, request):
        """Add a prior art document"""
        serializer = PriorArtDocumentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            document = serializer.save()
            
            # Trigger prior art analysis task
            search_prior_art_task.delay(document.id, request.user.id)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClaimChartView(APIView):
    """
    Manage claim charts for infringement and invalidity analysis.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get claim charts for an analysis run",
        tags=["IP Litigation - Claim Charts"],
        manual_parameters=[
            openapi.Parameter('analysis_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('chart_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False)
        ],
        responses={200: ClaimChartSerializer(many=True)}
    )
    def get(self, request):
        """Get claim charts for an analysis run"""
        analysis_run_id = request.query_params.get('analysis_run_id')
        if not analysis_run_id:
            return Response({"error": "analysis_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the analysis run
        analysis_run = get_object_or_404(PatentAnalysisRun, pk=analysis_run_id, run__user=request.user)

        charts = ClaimChart.objects.filter(
            analysis_run=analysis_run,
            user=request.user
        )

        # Apply chart type filter
        chart_type = request.query_params.get('chart_type')
        if chart_type:
            charts = charts.filter(chart_type=chart_type)

        serializer = ClaimChartSerializer(charts, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Create a new claim chart",
        tags=["IP Litigation - Claim Charts"],
        request_body=ClaimChartSerializer,
        responses={201: ClaimChartSerializer}
    )
    def post(self, request):
        """Create a new claim chart"""
        serializer = ClaimChartSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            chart = serializer.save()

            # Trigger claim chart generation task
            generate_claim_chart_task.delay(chart.id, request.user.id)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClaimChartDetailView(APIView):
    """
    Retrieve, update, and delete claim charts.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get claim chart details",
        tags=["IP Litigation - Claim Charts"],
        responses={200: ClaimChartSerializer}
    )
    def get(self, request, pk):
        """Get claim chart details"""
        chart = get_object_or_404(ClaimChart, pk=pk, user=request.user)
        serializer = ClaimChartSerializer(chart)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Update claim chart",
        tags=["IP Litigation - Claim Charts"],
        request_body=ClaimChartSerializer,
        responses={200: ClaimChartSerializer}
    )
    def put(self, request, pk):
        """Update claim chart"""
        chart = get_object_or_404(ClaimChart, pk=pk, user=request.user)
        serializer = ClaimChartSerializer(chart, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Delete claim chart",
        tags=["IP Litigation - Claim Charts"],
        responses={204: "Claim chart deleted"}
    )
    def delete(self, request, pk):
        """Delete claim chart"""
        chart = get_object_or_404(ClaimChart, pk=pk, user=request.user)
        chart.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InfringementAnalysisView(APIView):
    """
    Manage infringement analyses for patent litigation.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get infringement analyses for an analysis run",
        tags=["IP Litigation - Infringement Analysis"],
        manual_parameters=[
            openapi.Parameter('analysis_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: InfringementAnalysisSerializer(many=True)}
    )
    def get(self, request):
        """Get infringement analyses for an analysis run"""
        analysis_run_id = request.query_params.get('analysis_run_id')
        if not analysis_run_id:
            return Response({"error": "analysis_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the analysis run
        analysis_run = get_object_or_404(PatentAnalysisRun, pk=analysis_run_id, run__user=request.user)

        analyses = InfringementAnalysis.objects.filter(
            analysis_run=analysis_run,
            user=request.user
        )
        serializer = InfringementAnalysisSerializer(analyses, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Create a new infringement analysis",
        tags=["IP Litigation - Infringement Analysis"],
        request_body=InfringementAnalysisSerializer,
        responses={201: InfringementAnalysisSerializer}
    )
    def post(self, request):
        """Create a new infringement analysis"""
        serializer = InfringementAnalysisSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            analysis = serializer.save()

            # Trigger infringement analysis task
            analyze_infringement_task.delay(analysis.id, request.user.id)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ValidityChallengeView(APIView):
    """
    Manage patent validity challenges.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get validity challenges for an analysis run",
        tags=["IP Litigation - Validity Challenges"],
        manual_parameters=[
            openapi.Parameter('analysis_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: ValidityChallengeSerializer(many=True)}
    )
    def get(self, request):
        """Get validity challenges for an analysis run"""
        analysis_run_id = request.query_params.get('analysis_run_id')
        if not analysis_run_id:
            return Response({"error": "analysis_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the analysis run
        analysis_run = get_object_or_404(PatentAnalysisRun, pk=analysis_run_id, run__user=request.user)

        challenges = ValidityChallenge.objects.filter(
            analysis_run=analysis_run,
            user=request.user
        )
        serializer = ValidityChallengeSerializer(challenges, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Create a new validity challenge",
        tags=["IP Litigation - Validity Challenges"],
        request_body=ValidityChallengeSerializer,
        responses={201: ValidityChallengeSerializer}
    )
    def post(self, request):
        """Create a new validity challenge"""
        serializer = ValidityChallengeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            challenge = serializer.save()

            # Trigger validity analysis task
            analyze_validity_task.delay(challenge.id, request.user.id)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PatentAnalysisSummaryView(APIView):
    """
    Get summary statistics for patent analysis.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get patent analysis summary statistics",
        tags=["IP Litigation - Analytics"],
        manual_parameters=[
            openapi.Parameter('analysis_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: PatentAnalysisSummarySerializer}
    )
    def get(self, request):
        """Get patent analysis summary statistics"""
        analysis_run_id = request.query_params.get('analysis_run_id')
        if not analysis_run_id:
            return Response({"error": "analysis_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the analysis run
        analysis_run = get_object_or_404(PatentAnalysisRun, pk=analysis_run_id, run__user=request.user)

        # Get summary statistics
        patents = PatentDocument.objects.filter(analysis_run=analysis_run, user=request.user)
        claims = PatentClaim.objects.filter(analysis_run=analysis_run, user=request.user)
        prior_art = PriorArtDocument.objects.filter(analysis_run=analysis_run, user=request.user)
        claim_charts = ClaimChart.objects.filter(analysis_run=analysis_run, user=request.user)
        infringement_analyses = InfringementAnalysis.objects.filter(analysis_run=analysis_run, user=request.user)
        validity_challenges = ValidityChallenge.objects.filter(analysis_run=analysis_run, user=request.user)

        # Patent office breakdown
        patent_office_breakdown = {}
        for office_choice in PatentDocument._meta.get_field('patent_office').choices:
            office_code, office_name = office_choice
            count = patents.filter(patent_office=office_code).count()
            if count > 0:
                patent_office_breakdown[office_name] = count

        # Litigation type breakdown
        litigation_type_breakdown = {
            analysis_run.get_litigation_type_display(): 1
        }

        # Technology area breakdown
        technology_area_breakdown = {}
        if analysis_run.technology_area:
            technology_area_breakdown[analysis_run.technology_area] = patents.count()

        summary_data = {
            'total_patents': patents.count(),
            'total_claims': claims.count(),
            'total_prior_art': prior_art.count(),
            'total_claim_charts': claim_charts.count(),
            'infringement_analyses': infringement_analyses.count(),
            'validity_challenges': validity_challenges.count(),
            'patent_office_breakdown': patent_office_breakdown,
            'litigation_type_breakdown': litigation_type_breakdown,
            'technology_area_breakdown': technology_area_breakdown
        }

        serializer = PatentAnalysisSummarySerializer(summary_data)
        return Response(serializer.data)


class ClaimChartSummaryView(APIView):
    """
    Get summary statistics for claim charts.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get claim chart summary statistics",
        tags=["IP Litigation - Analytics"],
        manual_parameters=[
            openapi.Parameter('analysis_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: ClaimChartSummarySerializer(many=True)}
    )
    def get(self, request):
        """Get claim chart summary statistics"""
        analysis_run_id = request.query_params.get('analysis_run_id')
        if not analysis_run_id:
            return Response({"error": "analysis_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the analysis run
        analysis_run = get_object_or_404(PatentAnalysisRun, pk=analysis_run_id, run__user=request.user)

        # Get summary statistics grouped by chart type
        summary_data = []
        chart_types = ClaimChart.objects.filter(
            analysis_run=analysis_run,
            user=request.user
        ).values_list('chart_type', flat=True).distinct()

        for chart_type in chart_types:
            charts = ClaimChart.objects.filter(
                analysis_run=analysis_run,
                user=request.user,
                chart_type=chart_type
            )

            summary_data.append({
                'chart_type': chart_type,
                'chart_type_display': dict(ClaimChart._meta.get_field('chart_type').choices)[chart_type],
                'total_count': charts.count(),
                'infringes_count': charts.filter(overall_conclusion='infringes').count(),
                'does_not_infringe_count': charts.filter(overall_conclusion='does_not_infringe').count(),
                'unclear_count': charts.filter(overall_conclusion='unclear').count(),
                'avg_confidence_score': charts.aggregate(Avg('confidence_score'))['confidence_score__avg'] or 0.0,
            })

        serializer = ClaimChartSummarySerializer(summary_data, many=True)
        return Response(serializer.data)


class InfringementSummaryView(APIView):
    """
    Get summary statistics for infringement analyses.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get infringement analysis summary statistics",
        tags=["IP Litigation - Analytics"],
        manual_parameters=[
            openapi.Parameter('analysis_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: InfringementSummarySerializer}
    )
    def get(self, request):
        """Get infringement analysis summary statistics"""
        analysis_run_id = request.query_params.get('analysis_run_id')
        if not analysis_run_id:
            return Response({"error": "analysis_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the analysis run
        analysis_run = get_object_or_404(PatentAnalysisRun, pk=analysis_run_id, run__user=request.user)

        # Get infringement analysis summary
        analyses = InfringementAnalysis.objects.filter(
            analysis_run=analysis_run,
            user=request.user
        )

        total_analyses = analyses.count()
        if total_analyses == 0:
            summary_data = {
                'total_analyses': 0,
                'infringement_found': 0,
                'no_infringement': 0,
                'mixed_results': 0,
                'inconclusive': 0,
                'literal_infringement_rate': 0.0,
                'doe_infringement_rate': 0.0,
                'high_confidence_analyses': 0
            }
        else:
            infringement_found = analyses.filter(infringement_conclusion='infringes').count()
            no_infringement = analyses.filter(infringement_conclusion='does_not_infringe').count()
            mixed_results = analyses.filter(infringement_conclusion='mixed').count()
            inconclusive = analyses.filter(infringement_conclusion='inconclusive').count()

            literal_infringement = analyses.filter(literal_infringement='yes').count()
            doe_infringement = analyses.filter(doctrine_of_equivalents='yes').count()
            high_confidence = analyses.filter(confidence_level='high').count()

            summary_data = {
                'total_analyses': total_analyses,
                'infringement_found': infringement_found,
                'no_infringement': no_infringement,
                'mixed_results': mixed_results,
                'inconclusive': inconclusive,
                'literal_infringement_rate': (literal_infringement / total_analyses) * 100,
                'doe_infringement_rate': (doe_infringement / total_analyses) * 100,
                'high_confidence_analyses': high_confidence
            }

        serializer = InfringementSummarySerializer(summary_data)
        return Response(serializer.data)


class ValiditySummaryView(APIView):
    """
    Get summary statistics for validity challenges.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get validity challenge summary statistics",
        tags=["IP Litigation - Analytics"],
        manual_parameters=[
            openapi.Parameter('analysis_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: ValiditySummarySerializer}
    )
    def get(self, request):
        """Get validity challenge summary statistics"""
        analysis_run_id = request.query_params.get('analysis_run_id')
        if not analysis_run_id:
            return Response({"error": "analysis_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the analysis run
        analysis_run = get_object_or_404(PatentAnalysisRun, pk=analysis_run_id, run__user=request.user)

        # Get validity challenge summary
        challenges = ValidityChallenge.objects.filter(
            analysis_run=analysis_run,
            user=request.user
        )

        total_challenges = challenges.count()
        strong_challenges = challenges.filter(challenge_strength='strong').count()
        moderate_challenges = challenges.filter(challenge_strength='moderate').count()
        weak_challenges = challenges.filter(challenge_strength='weak').count()

        avg_success_likelihood = challenges.aggregate(Avg('success_likelihood'))['success_likelihood__avg'] or 0.0

        # Count challenges by ground
        anticipation_challenges = 0
        obviousness_challenges = 0
        for challenge in challenges:
            if 'anticipation' in challenge.challenge_grounds:
                anticipation_challenges += 1
            if 'obviousness' in challenge.challenge_grounds:
                obviousness_challenges += 1

        # Most challenged patents
        most_challenged_patents = []
        patent_challenge_counts = {}
        for challenge in challenges:
            patent_num = challenge.target_patent.patent_number
            patent_challenge_counts[patent_num] = patent_challenge_counts.get(patent_num, 0) + 1

        # Sort by challenge count and take top 5
        sorted_patents = sorted(patent_challenge_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        most_challenged_patents = [{'patent_number': patent, 'challenge_count': count} for patent, count in sorted_patents]

        summary_data = {
            'total_challenges': total_challenges,
            'strong_challenges': strong_challenges,
            'moderate_challenges': moderate_challenges,
            'weak_challenges': weak_challenges,
            'avg_success_likelihood': avg_success_likelihood,
            'anticipation_challenges': anticipation_challenges,
            'obviousness_challenges': obviousness_challenges,
            'most_challenged_patents': most_challenged_patents
        }

        serializer = ValiditySummarySerializer(summary_data)
        return Response(serializer.data)
