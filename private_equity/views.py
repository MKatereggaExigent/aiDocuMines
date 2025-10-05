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
    FindingsReport, DataRoomConnector, ServiceExecution, ServiceOutput
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

# Import AI services for enhanced document processing
try:
    from document_search.tasks import semantic_search_task, index_file
    from file_elasticsearch.utils import search_files
    AI_SERVICES_AVAILABLE = True
except ImportError:
    AI_SERVICES_AVAILABLE = False
    logger.warning("AI services not available - falling back to basic processing")


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


# ═══════════════════════════════════════════════════════════════
# 🔄 SERVICE EXECUTION & OUTPUT PERSISTENCE VIEWS
# ═══════════════════════════════════════════════════════════════

class ServiceExecutionListCreateView(APIView):
    """
    List and create service executions for Private Equity services.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="List all service executions for the authenticated user",
        tags=["Private Equity - Service Tracking"],
        responses={200: "List of service executions"}
    )
    def get(self, request):
        """List all service executions for the authenticated user"""
        executions = ServiceExecution.objects.filter(user=request.user)

        # Filter by due diligence run if provided
        dd_run_id = request.query_params.get('due_diligence_run')
        if dd_run_id:
            executions = executions.filter(due_diligence_run_id=dd_run_id)

        # Filter by service type if provided
        service_type = request.query_params.get('service_type')
        if service_type:
            executions = executions.filter(service_type=service_type)

        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            executions = executions.filter(status=status_filter)

        # Serialize and return
        data = []
        for execution in executions:
            data.append({
                'id': execution.id,
                'service_type': execution.service_type,
                'service_name': execution.service_name,
                'status': execution.status,
                'started_at': execution.started_at,
                'completed_at': execution.completed_at,
                'duration': execution.duration,
                'output_count': execution.output_count,
                'output_type': execution.output_type,
                'due_diligence_run': execution.due_diligence_run.id,
                'execution_metadata': execution.execution_metadata
            })

        return Response(data)

    @swagger_auto_schema(
        operation_description="Create a new service execution record",
        tags=["Private Equity - Service Tracking"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'service_type': openapi.Schema(type=openapi.TYPE_STRING),
                'service_name': openapi.Schema(type=openapi.TYPE_STRING),
                'due_diligence_run': openapi.Schema(type=openapi.TYPE_INTEGER),
                'input_parameters': openapi.Schema(type=openapi.TYPE_OBJECT),
                'output_type': openapi.Schema(type=openapi.TYPE_STRING),
                'execution_metadata': openapi.Schema(type=openapi.TYPE_OBJECT),
            }
        ),
        responses={201: "Service execution created"}
    )
    def post(self, request):
        """Create a new service execution record"""
        try:
            # Get or create due diligence run
            dd_run_id = request.data.get('due_diligence_run')
            if dd_run_id:
                dd_run = get_object_or_404(DueDiligenceRun, id=dd_run_id, run__user=request.user)
            else:
                # Create a default DD run if none provided
                from core.models import Run, Project
                project = Project.objects.filter(user=request.user).first()
                if not project:
                    return Response(
                        {'error': 'No project found. Please create a project first.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                run = Run.objects.create(
                    user=request.user,
                    project=project,
                    name=f"Service Execution Run - {request.data.get('service_name', 'Unknown')}"
                )

                dd_run = DueDiligenceRun.objects.create(
                    run=run,
                    deal_name=f"Auto-generated for {request.data.get('service_name', 'Service')}",
                    target_company="Auto-generated"
                )

            # Create service execution
            execution = ServiceExecution.objects.create(
                user=request.user,
                due_diligence_run=dd_run,
                service_type=request.data.get('service_type'),
                service_name=request.data.get('service_name'),
                service_version=request.data.get('service_version', '1.0'),
                status=request.data.get('status', 'completed'),
                input_parameters=request.data.get('input_parameters', {}),
                output_type=request.data.get('output_type', 'json'),
                output_count=request.data.get('output_count', 1),
                execution_metadata=request.data.get('execution_metadata', {})
            )

            # Set completed_at if status is completed
            if execution.status == 'completed':
                from django.utils import timezone
                execution.completed_at = timezone.now()
                execution.save()

            return Response({
                'id': execution.id,
                'service_type': execution.service_type,
                'service_name': execution.service_name,
                'status': execution.status,
                'created_at': execution.created_at
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating service execution: {str(e)}")
            return Response(
                {'error': f'Failed to create service execution: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class ServiceOutputListCreateView(APIView):
    """
    List and create service outputs for Private Equity services.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="List all service outputs for the authenticated user",
        tags=["Private Equity - Service Tracking"],
        responses={200: "List of service outputs"}
    )
    def get(self, request):
        """List all service outputs for the authenticated user"""
        outputs = ServiceOutput.objects.filter(service_execution__user=request.user)

        # Filter by service execution if provided
        execution_id = request.query_params.get('service_execution')
        if execution_id:
            outputs = outputs.filter(service_execution_id=execution_id)

        # Filter by output type if provided
        output_type = request.query_params.get('output_type')
        if output_type:
            outputs = outputs.filter(output_type=output_type)

        # Serialize and return
        data = []
        for output in outputs:
            data.append({
                'id': output.id,
                'service_execution': output.service_execution.id,
                'output_name': output.output_name,
                'output_type': output.output_type,
                'file_size': output.file_size,
                'formatted_size': output.formatted_size,
                'is_primary': output.is_primary,
                'created_at': output.created_at,
                'download_url': output.download_url,
                'preview_url': output.preview_url,
                'output_metadata': output.output_metadata
            })

        return Response(data)

    @swagger_auto_schema(
        operation_description="Create a new service output record",
        tags=["Private Equity - Service Tracking"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'service_execution': openapi.Schema(type=openapi.TYPE_STRING),
                'output_name': openapi.Schema(type=openapi.TYPE_STRING),
                'output_type': openapi.Schema(type=openapi.TYPE_STRING),
                'output_data': openapi.Schema(type=openapi.TYPE_OBJECT),
                'output_text': openapi.Schema(type=openapi.TYPE_STRING),
                'file_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                'output_metadata': openapi.Schema(type=openapi.TYPE_OBJECT),
                'is_primary': openapi.Schema(type=openapi.TYPE_BOOLEAN),
            }
        ),
        responses={201: "Service output created"}
    )
    def post(self, request):
        """Create a new service output record"""
        try:
            # Get service execution
            execution_id = request.data.get('service_execution')
            execution = get_object_or_404(ServiceExecution, id=execution_id, user=request.user)

            # Create service output
            output = ServiceOutput.objects.create(
                service_execution=execution,
                output_name=request.data.get('output_name'),
                output_type=request.data.get('output_type', 'json'),
                file_extension=request.data.get('file_extension', ''),
                mime_type=request.data.get('mime_type', ''),
                file_size=request.data.get('file_size'),
                output_data=request.data.get('output_data'),
                output_text=request.data.get('output_text', ''),
                download_url=request.data.get('download_url', ''),
                preview_url=request.data.get('preview_url', ''),
                output_metadata=request.data.get('output_metadata', {}),
                is_primary=request.data.get('is_primary', False)
            )

            # Update execution output count
            execution.output_count = execution.outputs.count()
            execution.save()

            return Response({
                'id': output.id,
                'output_name': output.output_name,
                'output_type': output.output_type,
                'created_at': output.created_at
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating service output: {str(e)}")
            return Response(
                {'error': f'Failed to create service output: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
