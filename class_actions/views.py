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
    MassClaimsRun, IntakeForm, EvidenceDocument, PIIRedaction,
    ExhibitPackage, SettlementTracking, ClaimantCommunication
)
from .serializers import (
    MassClaimsRunSerializer, MassClaimsRunCreateSerializer,
    IntakeFormSerializer, IntakeFormCreateSerializer,
    EvidenceDocumentSerializer, PIIRedactionSerializer,
    ExhibitPackageSerializer, SettlementTrackingSerializer,
    ClaimantCommunicationSerializer, EvidenceSummarySerializer,
    IntakeFormSummarySerializer
)
from .tasks import (
    process_intake_form_task, cull_evidence_documents_task,
    redact_pii_task, generate_exhibit_package_task,
    detect_duplicate_claims_task
)

logger = logging.getLogger(__name__)


class MassClaimsRunListCreateView(APIView):
    """
    List all mass claims runs for the authenticated user or create a new one.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    @swagger_auto_schema(
        operation_description="List all mass claims runs for the authenticated user",
        tags=["Class Actions - Mass Claims"],
        responses={200: MassClaimsRunSerializer(many=True)}
    )
    def get(self, request):
        """List all mass claims runs for the user"""
        runs = MassClaimsRun.objects.filter(run__user=request.user)
        serializer = MassClaimsRunSerializer(runs, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Create a new mass claims run",
        tags=["Class Actions - Mass Claims"],
        request_body=MassClaimsRunCreateSerializer,
        responses={201: MassClaimsRunSerializer}
    )
    def post(self, request):
        """Create a new mass claims run"""
        serializer = MassClaimsRunCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            mass_claims_run = serializer.save()
            response_serializer = MassClaimsRunSerializer(mass_claims_run)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MassClaimsRunDetailView(APIView):
    """
    Retrieve, update or delete a specific mass claims run.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    def get_object(self, pk, user):
        """Get mass claims run ensuring user ownership"""
        return get_object_or_404(MassClaimsRun, pk=pk, run__user=user)
    
    @swagger_auto_schema(
        operation_description="Retrieve a specific mass claims run",
        tags=["Class Actions - Mass Claims"],
        responses={200: MassClaimsRunSerializer}
    )
    def get(self, request, pk):
        """Retrieve a specific mass claims run"""
        mc_run = self.get_object(pk, request.user)
        serializer = MassClaimsRunSerializer(mc_run)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Update a specific mass claims run",
        tags=["Class Actions - Mass Claims"],
        request_body=MassClaimsRunSerializer,
        responses={200: MassClaimsRunSerializer}
    )
    def put(self, request, pk):
        """Update a specific mass claims run"""
        mc_run = self.get_object(pk, request.user)
        serializer = MassClaimsRunSerializer(mc_run, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Delete a specific mass claims run",
        tags=["Class Actions - Mass Claims"],
        responses={204: "No Content"}
    )
    def delete(self, request, pk):
        """Delete a specific mass claims run"""
        mc_run = self.get_object(pk, request.user)
        mc_run.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IntakeFormView(APIView):
    """
    Manage intake forms for mass claims.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    @swagger_auto_schema(
        operation_description="Get intake forms for a mass claims run",
        tags=["Class Actions - Intake Forms"],
        manual_parameters=[
            openapi.Parameter('mc_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False)
        ],
        responses={200: IntakeFormSerializer(many=True)}
    )
    def get(self, request):
        """Get intake forms for a mass claims run with optional filtering"""
        mc_run_id = request.query_params.get('mc_run_id')
        if not mc_run_id:
            return Response({"error": "mc_run_id parameter is required"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure user owns the mass claims run
        mc_run = get_object_or_404(MassClaimsRun, pk=mc_run_id, run__user=request.user)
        
        intake_forms = IntakeForm.objects.filter(
            mass_claims_run=mc_run,
            user=request.user
        )
        
        # Apply status filter
        status_filter = request.query_params.get('status')
        if status_filter:
            intake_forms = intake_forms.filter(processing_status=status_filter)
        
        serializer = IntakeFormSerializer(intake_forms, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Submit a new intake form",
        tags=["Class Actions - Intake Forms"],
        request_body=IntakeFormCreateSerializer,
        responses={201: IntakeFormSerializer}
    )
    def post(self, request):
        """Submit a new intake form"""
        serializer = IntakeFormCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            intake_form = serializer.save()
            
            # Trigger processing task
            process_intake_form_task.delay(intake_form.id, request.user.id)
            
            response_serializer = IntakeFormSerializer(intake_form)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EvidenceDocumentView(APIView):
    """
    Manage evidence documents with culling and relevance scoring.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    @swagger_auto_schema(
        operation_description="Get evidence documents for a mass claims run",
        tags=["Class Actions - Evidence Management"],
        manual_parameters=[
            openapi.Parameter('mc_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('evidence_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('is_culled', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, required=False)
        ],
        responses={200: EvidenceDocumentSerializer(many=True)}
    )
    def get(self, request):
        """Get evidence documents for a mass claims run with optional filtering"""
        mc_run_id = request.query_params.get('mc_run_id')
        if not mc_run_id:
            return Response({"error": "mc_run_id parameter is required"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure user owns the mass claims run
        mc_run = get_object_or_404(MassClaimsRun, pk=mc_run_id, run__user=request.user)
        
        evidence_docs = EvidenceDocument.objects.filter(
            mass_claims_run=mc_run,
            user=request.user
        )
        
        # Apply filters
        evidence_type = request.query_params.get('evidence_type')
        if evidence_type:
            evidence_docs = evidence_docs.filter(evidence_type=evidence_type)
        
        is_culled = request.query_params.get('is_culled')
        if is_culled is not None:
            is_culled_bool = is_culled.lower() == 'true'
            evidence_docs = evidence_docs.filter(is_culled=is_culled_bool)
        
        serializer = EvidenceDocumentSerializer(evidence_docs, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Trigger evidence culling for documents",
        tags=["Class Actions - Evidence Management"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'mc_run_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'file_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER))
            },
            required=['mc_run_id', 'file_ids']
        ),
        responses={202: "Evidence culling started"}
    )
    def post(self, request):
        """Trigger evidence culling for documents"""
        mc_run_id = request.data.get('mc_run_id')
        file_ids = request.data.get('file_ids', [])
        
        if not mc_run_id or not file_ids:
            return Response(
                {"error": "mc_run_id and file_ids are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ensure user owns the mass claims run
        mc_run = get_object_or_404(MassClaimsRun, pk=mc_run_id, run__user=request.user)
        
        # Ensure user owns all files
        files = File.objects.filter(id__in=file_ids, user=request.user)
        if files.count() != len(file_ids):
            return Response(
                {"error": "Some files not found or not owned by user"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Trigger culling task
        task = cull_evidence_documents_task.delay(mc_run.id, file_ids, request.user.id)
        
        return Response({
            "message": "Evidence culling started",
            "task_id": task.id,
            "files_count": len(file_ids)
        }, status=status.HTTP_202_ACCEPTED)


class PIIRedactionView(APIView):
    """
    Manage PII redaction for documents.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    @swagger_auto_schema(
        operation_description="Get PII redactions for a mass claims run",
        tags=["Class Actions - PII Redaction"],
        manual_parameters=[
            openapi.Parameter('mc_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('pii_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False)
        ],
        responses={200: PIIRedactionSerializer(many=True)}
    )
    def get(self, request):
        """Get PII redactions for a mass claims run"""
        mc_run_id = request.query_params.get('mc_run_id')
        if not mc_run_id:
            return Response({"error": "mc_run_id parameter is required"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure user owns the mass claims run
        mc_run = get_object_or_404(MassClaimsRun, pk=mc_run_id, run__user=request.user)
        
        redactions = PIIRedaction.objects.filter(
            mass_claims_run=mc_run,
            user=request.user
        )
        
        # Apply PII type filter
        pii_type = request.query_params.get('pii_type')
        if pii_type:
            redactions = redactions.filter(pii_type=pii_type)
        
        serializer = PIIRedactionSerializer(redactions, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Trigger PII redaction for documents",
        tags=["Class Actions - PII Redaction"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'mc_run_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'file_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER))
            },
            required=['mc_run_id', 'file_ids']
        ),
        responses={202: "PII redaction started"}
    )
    def post(self, request):
        """Trigger PII redaction for documents"""
        mc_run_id = request.data.get('mc_run_id')
        file_ids = request.data.get('file_ids', [])
        
        if not mc_run_id or not file_ids:
            return Response(
                {"error": "mc_run_id and file_ids are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ensure user owns the mass claims run
        mc_run = get_object_or_404(MassClaimsRun, pk=mc_run_id, run__user=request.user)
        
        # Ensure user owns all files
        files = File.objects.filter(id__in=file_ids, user=request.user)
        if files.count() != len(file_ids):
            return Response(
                {"error": "Some files not found or not owned by user"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Trigger PII redaction task
        task = redact_pii_task.delay(mc_run.id, file_ids, request.user.id)
        
        return Response({
            "message": "PII redaction started",
            "task_id": task.id,
            "files_count": len(file_ids)
        }, status=status.HTTP_202_ACCEPTED)


class ExhibitPackageView(APIView):
    """
    Manage exhibit packages with Bates stamping.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get exhibit packages for a mass claims run",
        tags=["Class Actions - Exhibit Management"],
        manual_parameters=[
            openapi.Parameter('mc_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: ExhibitPackageSerializer(many=True)}
    )
    def get(self, request):
        """Get exhibit packages for a mass claims run"""
        mc_run_id = request.query_params.get('mc_run_id')
        if not mc_run_id:
            return Response({"error": "mc_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the mass claims run
        mc_run = get_object_or_404(MassClaimsRun, pk=mc_run_id, run__user=request.user)

        packages = ExhibitPackage.objects.filter(
            mass_claims_run=mc_run,
            user=request.user
        )
        serializer = ExhibitPackageSerializer(packages, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Create a new exhibit package",
        tags=["Class Actions - Exhibit Management"],
        request_body=ExhibitPackageSerializer,
        responses={201: ExhibitPackageSerializer}
    )
    def post(self, request):
        """Create a new exhibit package"""
        serializer = ExhibitPackageSerializer(data=request.data)
        if serializer.is_valid():
            # Ensure user owns the mass claims run
            mc_run = get_object_or_404(MassClaimsRun, pk=request.data.get('mass_claims_run'), run__user=request.user)

            package = serializer.save(user=request.user)

            # Trigger package generation task if files are provided
            if package.files.exists():
                generate_exhibit_package_task.delay(package.id, request.user.id)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SettlementTrackingView(APIView):
    """
    Manage settlement tracking and distribution.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get settlement tracking for a mass claims run",
        tags=["Class Actions - Settlement"],
        manual_parameters=[
            openapi.Parameter('mc_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: SettlementTrackingSerializer(many=True)}
    )
    def get(self, request):
        """Get settlement tracking for a mass claims run"""
        mc_run_id = request.query_params.get('mc_run_id')
        if not mc_run_id:
            return Response({"error": "mc_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the mass claims run
        mc_run = get_object_or_404(MassClaimsRun, pk=mc_run_id, run__user=request.user)

        settlements = SettlementTracking.objects.filter(
            mass_claims_run=mc_run,
            user=request.user
        )
        serializer = SettlementTrackingSerializer(settlements, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Create or update settlement tracking",
        tags=["Class Actions - Settlement"],
        request_body=SettlementTrackingSerializer,
        responses={201: SettlementTrackingSerializer}
    )
    def post(self, request):
        """Create or update settlement tracking"""
        serializer = SettlementTrackingSerializer(data=request.data)
        if serializer.is_valid():
            # Ensure user owns the mass claims run
            mc_run = get_object_or_404(MassClaimsRun, pk=request.data.get('mass_claims_run'), run__user=request.user)

            settlement = serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DuplicateDetectionView(APIView):
    """
    Detect duplicate intake forms.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Trigger duplicate detection for intake forms",
        tags=["Class Actions - Duplicate Detection"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'mc_run_id': openapi.Schema(type=openapi.TYPE_INTEGER)
            },
            required=['mc_run_id']
        ),
        responses={202: "Duplicate detection started"}
    )
    def post(self, request):
        """Trigger duplicate detection for intake forms"""
        mc_run_id = request.data.get('mc_run_id')

        if not mc_run_id:
            return Response(
                {"error": "mc_run_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure user owns the mass claims run
        mc_run = get_object_or_404(MassClaimsRun, pk=mc_run_id, run__user=request.user)

        # Trigger duplicate detection task
        task = detect_duplicate_claims_task.delay(mc_run.id, request.user.id)

        return Response({
            "message": "Duplicate detection started",
            "task_id": task.id,
            "mc_run_id": mc_run_id
        }, status=status.HTTP_202_ACCEPTED)


class EvidenceSummaryView(APIView):
    """
    Get summary statistics for evidence documents.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get evidence document summary statistics",
        tags=["Class Actions - Analytics"],
        manual_parameters=[
            openapi.Parameter('mc_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: EvidenceSummarySerializer(many=True)}
    )
    def get(self, request):
        """Get evidence document summary statistics"""
        mc_run_id = request.query_params.get('mc_run_id')
        if not mc_run_id:
            return Response({"error": "mc_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the mass claims run
        mc_run = get_object_or_404(MassClaimsRun, pk=mc_run_id, run__user=request.user)

        # Get summary statistics grouped by evidence type
        summary_data = []
        evidence_types = EvidenceDocument.objects.filter(
            mass_claims_run=mc_run,
            user=request.user
        ).values_list('evidence_type', flat=True).distinct()

        for evidence_type in evidence_types:
            docs = EvidenceDocument.objects.filter(
                mass_claims_run=mc_run,
                user=request.user,
                evidence_type=evidence_type
            )

            summary_data.append({
                'evidence_type': evidence_type,
                'evidence_type_display': dict(EvidenceDocument._meta.get_field('evidence_type').choices)[evidence_type],
                'total_count': docs.count(),
                'culled_count': docs.filter(is_culled=True).count(),
                'pii_count': docs.filter(contains_pii=True).count(),
                'privileged_count': docs.exclude(privilege_status='none').count(),
                'avg_relevance_score': docs.aggregate(Avg('relevance_score'))['relevance_score__avg'] or 0.0,
            })

        serializer = EvidenceSummarySerializer(summary_data, many=True)
        return Response(serializer.data)


class IntakeFormSummaryView(APIView):
    """
    Get summary statistics for intake forms.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get intake form summary statistics",
        tags=["Class Actions - Analytics"],
        manual_parameters=[
            openapi.Parameter('mc_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: IntakeFormSummarySerializer(many=True)}
    )
    def get(self, request):
        """Get intake form summary statistics"""
        mc_run_id = request.query_params.get('mc_run_id')
        if not mc_run_id:
            return Response({"error": "mc_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the mass claims run
        mc_run = get_object_or_404(MassClaimsRun, pk=mc_run_id, run__user=request.user)

        # Get summary statistics grouped by processing status
        summary_data = []
        statuses = IntakeForm.objects.filter(
            mass_claims_run=mc_run,
            user=request.user
        ).values_list('processing_status', flat=True).distinct()

        for status_val in statuses:
            forms = IntakeForm.objects.filter(
                mass_claims_run=mc_run,
                user=request.user,
                processing_status=status_val
            )

            summary_data.append({
                'processing_status': status_val,
                'processing_status_display': dict(IntakeForm._meta.get_field('processing_status').choices)[status_val],
                'total_count': forms.count(),
                'duplicate_count': forms.filter(is_duplicate=True).count(),
                'valid_count': forms.filter(is_valid=True).count(),
            })

        serializer = IntakeFormSummarySerializer(summary_data, many=True)
        return Response(serializer.data)
