from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, Avg
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from oauth2_provider.contrib.rest_framework import OAuth2Authentication, TokenHasReadWriteScope
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging

from custom_authentication.permissions import IsClientOrAdmin, IsClientOrAdminOrSuperUser
from core.models import File
from .models import (
    DueDiligenceRun, DocumentClassification, RiskClause, 
    FindingsReport, DataRoomConnector
)
from .serializers import (
    DueDiligenceRunSerializer, DueDiligenceRunCreateSerializer,
    DocumentClassificationSerializer, RiskClauseSerializer,
    FindingsReportSerializer, DataRoomConnectorSerializer,
    RiskClauseSummarySerializer, DocumentTypeSummarySerializer
)
from .tasks import (
    classify_document_task, extract_risk_clauses_task,
    generate_findings_report_task, sync_data_room_task
)

logger = logging.getLogger(__name__)


class DueDiligenceRunListCreateView(APIView):
    """
    List all due diligence runs for the authenticated user or create a new one.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    @swagger_auto_schema(
        operation_description="List all due diligence runs for the authenticated user",
        tags=["Private Equity - Due Diligence"],
        responses={200: DueDiligenceRunSerializer(many=True)}
    )
    def get(self, request):
        """List all due diligence runs for the user"""
        runs = DueDiligenceRun.objects.filter(run__user=request.user)
        serializer = DueDiligenceRunSerializer(runs, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Create a new due diligence run",
        tags=["Private Equity - Due Diligence"],
        request_body=DueDiligenceRunCreateSerializer,
        responses={201: DueDiligenceRunSerializer}
    )
    def post(self, request):
        """Create a new due diligence run"""
        serializer = DueDiligenceRunCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            due_diligence_run = serializer.save()
            response_serializer = DueDiligenceRunSerializer(due_diligence_run)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DueDiligenceRunDetailView(APIView):
    """
    Retrieve, update or delete a specific due diligence run.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    def get_object(self, pk, user):
        """Get due diligence run ensuring user ownership"""
        return get_object_or_404(DueDiligenceRun, pk=pk, run__user=user)
    
    @swagger_auto_schema(
        operation_description="Retrieve a specific due diligence run",
        tags=["Private Equity - Due Diligence"],
        responses={200: DueDiligenceRunSerializer}
    )
    def get(self, request, pk):
        """Retrieve a specific due diligence run"""
        dd_run = self.get_object(pk, request.user)
        serializer = DueDiligenceRunSerializer(dd_run)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Update a specific due diligence run",
        tags=["Private Equity - Due Diligence"],
        request_body=DueDiligenceRunSerializer,
        responses={200: DueDiligenceRunSerializer}
    )
    def put(self, request, pk):
        """Update a specific due diligence run"""
        dd_run = self.get_object(pk, request.user)
        serializer = DueDiligenceRunSerializer(dd_run, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Delete a specific due diligence run",
        tags=["Private Equity - Due Diligence"],
        responses={204: "No Content"}
    )
    def delete(self, request, pk):
        """Delete a specific due diligence run"""
        dd_run = self.get_object(pk, request.user)
        dd_run.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentClassificationView(APIView):
    """
    Auto-classify documents or retrieve classification results.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    @swagger_auto_schema(
        operation_description="Get document classifications for a due diligence run",
        tags=["Private Equity - Document Classification"],
        manual_parameters=[
            openapi.Parameter('dd_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: DocumentClassificationSerializer(many=True)}
    )
    def get(self, request):
        """Get document classifications for a due diligence run"""
        dd_run_id = request.query_params.get('dd_run_id')
        if not dd_run_id:
            return Response({"error": "dd_run_id parameter is required"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure user owns the DD run
        dd_run = get_object_or_404(DueDiligenceRun, pk=dd_run_id, run__user=request.user)
        
        classifications = DocumentClassification.objects.filter(
            due_diligence_run=dd_run,
            user=request.user
        )
        serializer = DocumentClassificationSerializer(classifications, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Trigger document classification for uploaded files",
        tags=["Private Equity - Document Classification"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'dd_run_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'file_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER))
            },
            required=['dd_run_id', 'file_ids']
        ),
        responses={202: "Classification started"}
    )
    def post(self, request):
        """Trigger document classification for uploaded files"""
        dd_run_id = request.data.get('dd_run_id')
        file_ids = request.data.get('file_ids', [])
        
        if not dd_run_id or not file_ids:
            return Response(
                {"error": "dd_run_id and file_ids are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ensure user owns the DD run
        dd_run = get_object_or_404(DueDiligenceRun, pk=dd_run_id, run__user=request.user)
        
        # Ensure user owns all files
        files = File.objects.filter(id__in=file_ids, user=request.user)
        if files.count() != len(file_ids):
            return Response(
                {"error": "Some files not found or not owned by user"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Trigger classification tasks
        task_ids = []
        for file_obj in files:
            task = classify_document_task.delay(file_obj.id, dd_run.id, request.user.id)
            task_ids.append(task.id)
        
        return Response({
            "message": "Document classification started",
            "task_ids": task_ids,
            "files_count": len(file_ids)
        }, status=status.HTTP_202_ACCEPTED)


class RiskClauseExtractionView(APIView):
    """
    Extract and manage risk clauses from documents.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    @swagger_auto_schema(
        operation_description="Get risk clauses for a due diligence run",
        tags=["Private Equity - Risk Analysis"],
        manual_parameters=[
            openapi.Parameter('dd_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('risk_level', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('clause_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False)
        ],
        responses={200: RiskClauseSerializer(many=True)}
    )
    def get(self, request):
        """Get risk clauses for a due diligence run with optional filtering"""
        dd_run_id = request.query_params.get('dd_run_id')
        if not dd_run_id:
            return Response({"error": "dd_run_id parameter is required"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure user owns the DD run
        dd_run = get_object_or_404(DueDiligenceRun, pk=dd_run_id, run__user=request.user)
        
        risk_clauses = RiskClause.objects.filter(
            due_diligence_run=dd_run,
            user=request.user
        )
        
        # Apply filters
        risk_level = request.query_params.get('risk_level')
        if risk_level:
            risk_clauses = risk_clauses.filter(risk_level=risk_level)
        
        clause_type = request.query_params.get('clause_type')
        if clause_type:
            risk_clauses = risk_clauses.filter(clause_type=clause_type)
        
        serializer = RiskClauseSerializer(risk_clauses, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Trigger risk clause extraction for documents",
        tags=["Private Equity - Risk Analysis"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'dd_run_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'file_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER))
            },
            required=['dd_run_id', 'file_ids']
        ),
        responses={202: "Risk extraction started"}
    )
    def post(self, request):
        """Trigger risk clause extraction for documents"""
        dd_run_id = request.data.get('dd_run_id')
        file_ids = request.data.get('file_ids', [])
        
        if not dd_run_id or not file_ids:
            return Response(
                {"error": "dd_run_id and file_ids are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ensure user owns the DD run
        dd_run = get_object_or_404(DueDiligenceRun, pk=dd_run_id, run__user=request.user)
        
        # Ensure user owns all files
        files = File.objects.filter(id__in=file_ids, user=request.user)
        if files.count() != len(file_ids):
            return Response(
                {"error": "Some files not found or not owned by user"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Trigger risk extraction tasks
        task_ids = []
        for file_obj in files:
            task = extract_risk_clauses_task.delay(file_obj.id, dd_run.id, request.user.id)
            task_ids.append(task.id)
        
        return Response({
            "message": "Risk clause extraction started",
            "task_ids": task_ids,
            "files_count": len(file_ids)
        }, status=status.HTTP_202_ACCEPTED)


class FindingsReportView(APIView):
    """
    Generate and manage findings reports for due diligence runs.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get findings reports for a due diligence run",
        tags=["Private Equity - Reports"],
        manual_parameters=[
            openapi.Parameter('dd_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: FindingsReportSerializer(many=True)}
    )
    def get(self, request):
        """Get findings reports for a due diligence run"""
        dd_run_id = request.query_params.get('dd_run_id')
        if not dd_run_id:
            return Response({"error": "dd_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the DD run
        dd_run = get_object_or_404(DueDiligenceRun, pk=dd_run_id, run__user=request.user)

        reports = FindingsReport.objects.filter(
            due_diligence_run=dd_run,
            user=request.user
        )
        serializer = FindingsReportSerializer(reports, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Generate a new findings report",
        tags=["Private Equity - Reports"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'dd_run_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'report_name': openapi.Schema(type=openapi.TYPE_STRING)
            },
            required=['dd_run_id']
        ),
        responses={202: "Report generation started"}
    )
    def post(self, request):
        """Generate a new findings report"""
        dd_run_id = request.data.get('dd_run_id')
        report_name = request.data.get('report_name', 'Due Diligence Findings Report')

        if not dd_run_id:
            return Response(
                {"error": "dd_run_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure user owns the DD run
        dd_run = get_object_or_404(DueDiligenceRun, pk=dd_run_id, run__user=request.user)

        # Trigger report generation task
        task = generate_findings_report_task.delay(dd_run.id, request.user.id, report_name)

        return Response({
            "message": "Findings report generation started",
            "task_id": task.id,
            "dd_run_id": dd_run_id
        }, status=status.HTTP_202_ACCEPTED)


class RiskClauseSummaryView(APIView):
    """
    Get summary statistics for risk clauses in a due diligence run.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get risk clause summary statistics",
        tags=["Private Equity - Analytics"],
        manual_parameters=[
            openapi.Parameter('dd_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: RiskClauseSummarySerializer(many=True)}
    )
    def get(self, request):
        """Get risk clause summary statistics for a due diligence run"""
        dd_run_id = request.query_params.get('dd_run_id')
        if not dd_run_id:
            return Response({"error": "dd_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the DD run
        dd_run = get_object_or_404(DueDiligenceRun, pk=dd_run_id, run__user=request.user)

        # Get summary statistics grouped by clause type
        summary_data = []
        clause_types = RiskClause.objects.filter(
            due_diligence_run=dd_run,
            user=request.user
        ).values_list('clause_type', flat=True).distinct()

        for clause_type in clause_types:
            clauses = RiskClause.objects.filter(
                due_diligence_run=dd_run,
                user=request.user,
                clause_type=clause_type
            )

            summary_data.append({
                'clause_type': clause_type,
                'clause_type_display': dict(RiskClause._meta.get_field('clause_type').choices)[clause_type],
                'total_count': clauses.count(),
                'high_risk_count': clauses.filter(risk_level='high').count(),
                'medium_risk_count': clauses.filter(risk_level='medium').count(),
                'low_risk_count': clauses.filter(risk_level='low').count(),
                'critical_risk_count': clauses.filter(risk_level='critical').count(),
            })

        serializer = RiskClauseSummarySerializer(summary_data, many=True)
        return Response(serializer.data)


class DocumentTypeSummaryView(APIView):
    """
    Get summary statistics for document classifications in a due diligence run.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get document type summary statistics",
        tags=["Private Equity - Analytics"],
        manual_parameters=[
            openapi.Parameter('dd_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: DocumentTypeSummarySerializer(many=True)}
    )
    def get(self, request):
        """Get document type summary statistics for a due diligence run"""
        dd_run_id = request.query_params.get('dd_run_id')
        if not dd_run_id:
            return Response({"error": "dd_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the DD run
        dd_run = get_object_or_404(DueDiligenceRun, pk=dd_run_id, run__user=request.user)

        # Get summary statistics grouped by document type
        summary_data = []
        doc_types = DocumentClassification.objects.filter(
            due_diligence_run=dd_run,
            user=request.user
        ).values_list('document_type', flat=True).distinct()

        for doc_type in doc_types:
            classifications = DocumentClassification.objects.filter(
                due_diligence_run=dd_run,
                user=request.user,
                document_type=doc_type
            )

            summary_data.append({
                'document_type': doc_type,
                'document_type_display': dict(DocumentClassification._meta.get_field('document_type').choices)[doc_type],
                'total_count': classifications.count(),
                'verified_count': classifications.filter(is_verified=True).count(),
                'avg_confidence_score': classifications.aggregate(Avg('confidence_score'))['confidence_score__avg'] or 0.0,
            })

        serializer = DocumentTypeSummarySerializer(summary_data, many=True)
        return Response(serializer.data)
