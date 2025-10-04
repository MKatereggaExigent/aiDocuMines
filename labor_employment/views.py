from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, Avg, Sum
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
    WorkplaceCommunicationsRun, CommunicationMessage, WageHourAnalysis,
    PolicyComparison, EEOCPacket, CommunicationPattern, ComplianceAlert
)
from .serializers import (
    WorkplaceCommunicationsRunSerializer, WorkplaceCommunicationsRunCreateSerializer,
    CommunicationMessageSerializer, WageHourAnalysisSerializer,
    PolicyComparisonSerializer, EEOCPacketSerializer,
    CommunicationPatternSerializer, ComplianceAlertSerializer,
    MessageAnalysisSummarySerializer, ComplianceAlertSummarySerializer,
    WageHourSummarySerializer
)
from .tasks import (
    analyze_communications_task, analyze_wage_hour_task,
    compare_policies_task, generate_eeoc_packet_task,
    detect_communication_patterns_task
)

logger = logging.getLogger(__name__)


class WorkplaceCommunicationsRunListCreateView(APIView):
    """
    List all workplace communications runs for the authenticated user or create a new one.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    @swagger_auto_schema(
        operation_description="List all workplace communications runs for the authenticated user",
        tags=["Labor Employment - Communications"],
        responses={200: WorkplaceCommunicationsRunSerializer(many=True)}
    )
    def get(self, request):
        """List all workplace communications runs for the user"""
        runs = WorkplaceCommunicationsRun.objects.filter(run__user=request.user)
        serializer = WorkplaceCommunicationsRunSerializer(runs, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Create a new workplace communications run",
        tags=["Labor Employment - Communications"],
        request_body=WorkplaceCommunicationsRunCreateSerializer,
        responses={201: WorkplaceCommunicationsRunSerializer}
    )
    def post(self, request):
        """Create a new workplace communications run"""
        serializer = WorkplaceCommunicationsRunCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            communications_run = serializer.save()
            response_serializer = WorkplaceCommunicationsRunSerializer(communications_run)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkplaceCommunicationsRunDetailView(APIView):
    """
    Retrieve, update or delete a specific workplace communications run.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    def get_object(self, pk, user):
        """Get communications run ensuring user ownership"""
        return get_object_or_404(WorkplaceCommunicationsRun, pk=pk, run__user=user)
    
    @swagger_auto_schema(
        operation_description="Retrieve a specific workplace communications run",
        tags=["Labor Employment - Communications"],
        responses={200: WorkplaceCommunicationsRunSerializer}
    )
    def get(self, request, pk):
        """Retrieve a specific workplace communications run"""
        comm_run = self.get_object(pk, request.user)
        serializer = WorkplaceCommunicationsRunSerializer(comm_run)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Update a specific workplace communications run",
        tags=["Labor Employment - Communications"],
        request_body=WorkplaceCommunicationsRunSerializer,
        responses={200: WorkplaceCommunicationsRunSerializer}
    )
    def put(self, request, pk):
        """Update a specific workplace communications run"""
        comm_run = self.get_object(pk, request.user)
        serializer = WorkplaceCommunicationsRunSerializer(comm_run, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Delete a specific workplace communications run",
        tags=["Labor Employment - Communications"],
        responses={204: "No Content"}
    )
    def delete(self, request, pk):
        """Delete a specific workplace communications run"""
        comm_run = self.get_object(pk, request.user)
        comm_run.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CommunicationAnalysisView(APIView):
    """
    Analyze workplace communications for sentiment, toxicity, and compliance issues.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    @swagger_auto_schema(
        operation_description="Get communication messages for a workplace communications run",
        tags=["Labor Employment - Message Analysis"],
        manual_parameters=[
            openapi.Parameter('comm_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('message_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('is_flagged', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, required=False)
        ],
        responses={200: CommunicationMessageSerializer(many=True)}
    )
    def get(self, request):
        """Get communication messages with optional filtering"""
        comm_run_id = request.query_params.get('comm_run_id')
        if not comm_run_id:
            return Response({"error": "comm_run_id parameter is required"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure user owns the communications run
        comm_run = get_object_or_404(WorkplaceCommunicationsRun, pk=comm_run_id, run__user=request.user)
        
        messages = CommunicationMessage.objects.filter(
            communications_run=comm_run,
            user=request.user
        )
        
        # Apply filters
        message_type = request.query_params.get('message_type')
        if message_type:
            messages = messages.filter(message_type=message_type)
        
        is_flagged = request.query_params.get('is_flagged')
        if is_flagged is not None:
            is_flagged_bool = is_flagged.lower() == 'true'
            messages = messages.filter(is_flagged=is_flagged_bool)
        
        serializer = CommunicationMessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Trigger communication analysis for uploaded files",
        tags=["Labor Employment - Message Analysis"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'comm_run_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'file_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER))
            },
            required=['comm_run_id', 'file_ids']
        ),
        responses={202: "Communication analysis started"}
    )
    def post(self, request):
        """Trigger communication analysis for uploaded files"""
        comm_run_id = request.data.get('comm_run_id')
        file_ids = request.data.get('file_ids', [])
        
        if not comm_run_id or not file_ids:
            return Response(
                {"error": "comm_run_id and file_ids are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ensure user owns the communications run
        comm_run = get_object_or_404(WorkplaceCommunicationsRun, pk=comm_run_id, run__user=request.user)
        
        # Ensure user owns all files
        files = File.objects.filter(id__in=file_ids, user=request.user)
        if files.count() != len(file_ids):
            return Response(
                {"error": "Some files not found or not owned by user"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Trigger analysis task
        task = analyze_communications_task.delay(comm_run.id, file_ids, request.user.id)
        
        return Response({
            "message": "Communication analysis started",
            "task_id": task.id,
            "files_count": len(file_ids)
        }, status=status.HTTP_202_ACCEPTED)


class WageHourAnalysisView(APIView):
    """
    Analyze wage and hour patterns from communications.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    @swagger_auto_schema(
        operation_description="Get wage hour analyses for a communications run",
        tags=["Labor Employment - Wage Hour"],
        manual_parameters=[
            openapi.Parameter('comm_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: WageHourAnalysisSerializer(many=True)}
    )
    def get(self, request):
        """Get wage hour analyses for a communications run"""
        comm_run_id = request.query_params.get('comm_run_id')
        if not comm_run_id:
            return Response({"error": "comm_run_id parameter is required"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure user owns the communications run
        comm_run = get_object_or_404(WorkplaceCommunicationsRun, pk=comm_run_id, run__user=request.user)
        
        analyses = WageHourAnalysis.objects.filter(
            communications_run=comm_run,
            user=request.user
        )
        serializer = WageHourAnalysisSerializer(analyses, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Trigger wage hour analysis",
        tags=["Labor Employment - Wage Hour"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'comm_run_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'employee_list': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING))
            },
            required=['comm_run_id']
        ),
        responses={202: "Wage hour analysis started"}
    )
    def post(self, request):
        """Trigger wage hour analysis"""
        comm_run_id = request.data.get('comm_run_id')
        employee_list = request.data.get('employee_list', [])
        
        if not comm_run_id:
            return Response(
                {"error": "comm_run_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ensure user owns the communications run
        comm_run = get_object_or_404(WorkplaceCommunicationsRun, pk=comm_run_id, run__user=request.user)
        
        # Trigger wage hour analysis task
        task = analyze_wage_hour_task.delay(comm_run.id, employee_list, request.user.id)
        
        return Response({
            "message": "Wage hour analysis started",
            "task_id": task.id,
            "employees_count": len(employee_list)
        }, status=status.HTTP_202_ACCEPTED)


class PolicyComparisonView(APIView):
    """
    Compare company policies against communications and best practices.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]
    
    @swagger_auto_schema(
        operation_description="Get policy comparisons for a communications run",
        tags=["Labor Employment - Policy Analysis"],
        manual_parameters=[
            openapi.Parameter('comm_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: PolicyComparisonSerializer(many=True)}
    )
    def get(self, request):
        """Get policy comparisons for a communications run"""
        comm_run_id = request.query_params.get('comm_run_id')
        if not comm_run_id:
            return Response({"error": "comm_run_id parameter is required"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure user owns the communications run
        comm_run = get_object_or_404(WorkplaceCommunicationsRun, pk=comm_run_id, run__user=request.user)
        
        comparisons = PolicyComparison.objects.filter(
            communications_run=comm_run,
            user=request.user
        )
        serializer = PolicyComparisonSerializer(comparisons, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Trigger policy comparison analysis",
        tags=["Labor Employment - Policy Analysis"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'comm_run_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'policy_file_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER))
            },
            required=['comm_run_id', 'policy_file_ids']
        ),
        responses={202: "Policy comparison started"}
    )
    def post(self, request):
        """Trigger policy comparison analysis"""
        comm_run_id = request.data.get('comm_run_id')
        policy_file_ids = request.data.get('policy_file_ids', [])
        
        if not comm_run_id or not policy_file_ids:
            return Response(
                {"error": "comm_run_id and policy_file_ids are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ensure user owns the communications run
        comm_run = get_object_or_404(WorkplaceCommunicationsRun, pk=comm_run_id, run__user=request.user)
        
        # Ensure user owns all policy files
        files = File.objects.filter(id__in=policy_file_ids, user=request.user)
        if files.count() != len(policy_file_ids):
            return Response(
                {"error": "Some policy files not found or not owned by user"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Trigger policy comparison task
        task = compare_policies_task.delay(comm_run.id, policy_file_ids, request.user.id)
        
        return Response({
            "message": "Policy comparison started",
            "task_id": task.id,
            "policy_files_count": len(policy_file_ids)
        }, status=status.HTTP_202_ACCEPTED)


class EEOCPacketView(APIView):
    """
    Generate and manage EEOC complaint packets.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get EEOC packets for a communications run",
        tags=["Labor Employment - EEOC"],
        manual_parameters=[
            openapi.Parameter('comm_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: EEOCPacketSerializer(many=True)}
    )
    def get(self, request):
        """Get EEOC packets for a communications run"""
        comm_run_id = request.query_params.get('comm_run_id')
        if not comm_run_id:
            return Response({"error": "comm_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the communications run
        comm_run = get_object_or_404(WorkplaceCommunicationsRun, pk=comm_run_id, run__user=request.user)

        packets = EEOCPacket.objects.filter(
            communications_run=comm_run,
            user=request.user
        )
        serializer = EEOCPacketSerializer(packets, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Generate a new EEOC packet",
        tags=["Labor Employment - EEOC"],
        request_body=EEOCPacketSerializer,
        responses={201: EEOCPacketSerializer}
    )
    def post(self, request):
        """Generate a new EEOC packet"""
        serializer = EEOCPacketSerializer(data=request.data)
        if serializer.is_valid():
            # Ensure user owns the communications run
            comm_run = get_object_or_404(WorkplaceCommunicationsRun, pk=request.data.get('communications_run'), run__user=request.user)

            packet = serializer.save(user=request.user)

            # Trigger EEOC packet generation task
            generate_eeoc_packet_task.delay(packet.id, request.user.id)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommunicationPatternView(APIView):
    """
    Detect and analyze communication patterns.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get communication patterns for a communications run",
        tags=["Labor Employment - Pattern Analysis"],
        manual_parameters=[
            openapi.Parameter('comm_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('pattern_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False)
        ],
        responses={200: CommunicationPatternSerializer(many=True)}
    )
    def get(self, request):
        """Get communication patterns for a communications run"""
        comm_run_id = request.query_params.get('comm_run_id')
        if not comm_run_id:
            return Response({"error": "comm_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the communications run
        comm_run = get_object_or_404(WorkplaceCommunicationsRun, pk=comm_run_id, run__user=request.user)

        patterns = CommunicationPattern.objects.filter(
            communications_run=comm_run,
            user=request.user
        )

        # Apply pattern type filter
        pattern_type = request.query_params.get('pattern_type')
        if pattern_type:
            patterns = patterns.filter(pattern_type=pattern_type)

        serializer = CommunicationPatternSerializer(patterns, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Trigger communication pattern detection",
        tags=["Labor Employment - Pattern Analysis"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'comm_run_id': openapi.Schema(type=openapi.TYPE_INTEGER)
            },
            required=['comm_run_id']
        ),
        responses={202: "Pattern detection started"}
    )
    def post(self, request):
        """Trigger communication pattern detection"""
        comm_run_id = request.data.get('comm_run_id')

        if not comm_run_id:
            return Response(
                {"error": "comm_run_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure user owns the communications run
        comm_run = get_object_or_404(WorkplaceCommunicationsRun, pk=comm_run_id, run__user=request.user)

        # Trigger pattern detection task
        task = detect_communication_patterns_task.delay(comm_run.id, request.user.id)

        return Response({
            "message": "Communication pattern detection started",
            "task_id": task.id,
            "comm_run_id": comm_run_id
        }, status=status.HTTP_202_ACCEPTED)


class ComplianceAlertView(APIView):
    """
    Manage compliance alerts for potential employment law issues.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get compliance alerts for a communications run",
        tags=["Labor Employment - Compliance"],
        manual_parameters=[
            openapi.Parameter('comm_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('severity', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False)
        ],
        responses={200: ComplianceAlertSerializer(many=True)}
    )
    def get(self, request):
        """Get compliance alerts with optional filtering"""
        comm_run_id = request.query_params.get('comm_run_id')
        if not comm_run_id:
            return Response({"error": "comm_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the communications run
        comm_run = get_object_or_404(WorkplaceCommunicationsRun, pk=comm_run_id, run__user=request.user)

        alerts = ComplianceAlert.objects.filter(
            communications_run=comm_run,
            user=request.user
        )

        # Apply filters
        severity = request.query_params.get('severity')
        if severity:
            alerts = alerts.filter(severity=severity)

        alert_status = request.query_params.get('status')
        if alert_status:
            alerts = alerts.filter(status=alert_status)

        serializer = ComplianceAlertSerializer(alerts, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Update compliance alert status",
        tags=["Labor Employment - Compliance"],
        request_body=ComplianceAlertSerializer,
        responses={200: ComplianceAlertSerializer}
    )
    def put(self, request, pk):
        """Update compliance alert status"""
        alert = get_object_or_404(ComplianceAlert, pk=pk, user=request.user)
        serializer = ComplianceAlertSerializer(alert, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MessageAnalysisSummaryView(APIView):
    """
    Get summary statistics for message analysis.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get message analysis summary statistics",
        tags=["Labor Employment - Analytics"],
        manual_parameters=[
            openapi.Parameter('comm_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: MessageAnalysisSummarySerializer(many=True)}
    )
    def get(self, request):
        """Get message analysis summary statistics"""
        comm_run_id = request.query_params.get('comm_run_id')
        if not comm_run_id:
            return Response({"error": "comm_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the communications run
        comm_run = get_object_or_404(WorkplaceCommunicationsRun, pk=comm_run_id, run__user=request.user)

        # Get summary statistics grouped by message type
        summary_data = []
        message_types = CommunicationMessage.objects.filter(
            communications_run=comm_run,
            user=request.user
        ).values_list('message_type', flat=True).distinct()

        for message_type in message_types:
            messages = CommunicationMessage.objects.filter(
                communications_run=comm_run,
                user=request.user,
                message_type=message_type
            )

            summary_data.append({
                'message_type': message_type,
                'message_type_display': dict(CommunicationMessage._meta.get_field('message_type').choices)[message_type],
                'total_count': messages.count(),
                'flagged_count': messages.filter(is_flagged=True).count(),
                'privileged_count': messages.filter(is_privileged=True).count(),
                'pii_count': messages.filter(contains_pii=True).count(),
                'avg_sentiment_score': messages.aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0.0,
                'avg_toxicity_score': messages.aggregate(Avg('toxicity_score'))['toxicity_score__avg'] or 0.0,
            })

        serializer = MessageAnalysisSummarySerializer(summary_data, many=True)
        return Response(serializer.data)


class ComplianceAlertSummaryView(APIView):
    """
    Get summary statistics for compliance alerts.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get compliance alert summary statistics",
        tags=["Labor Employment - Analytics"],
        manual_parameters=[
            openapi.Parameter('comm_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: ComplianceAlertSummarySerializer(many=True)}
    )
    def get(self, request):
        """Get compliance alert summary statistics"""
        comm_run_id = request.query_params.get('comm_run_id')
        if not comm_run_id:
            return Response({"error": "comm_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the communications run
        comm_run = get_object_or_404(WorkplaceCommunicationsRun, pk=comm_run_id, run__user=request.user)

        # Get summary statistics grouped by alert type
        summary_data = []
        alert_types = ComplianceAlert.objects.filter(
            communications_run=comm_run,
            user=request.user
        ).values_list('alert_type', flat=True).distinct()

        for alert_type in alert_types:
            alerts = ComplianceAlert.objects.filter(
                communications_run=comm_run,
                user=request.user,
                alert_type=alert_type
            )

            summary_data.append({
                'alert_type': alert_type,
                'alert_type_display': dict(ComplianceAlert._meta.get_field('alert_type').choices)[alert_type],
                'total_count': alerts.count(),
                'open_count': alerts.filter(status='open').count(),
                'critical_count': alerts.filter(severity='critical').count(),
                'high_count': alerts.filter(severity='high').count(),
            })

        serializer = ComplianceAlertSummarySerializer(summary_data, many=True)
        return Response(serializer.data)


class WageHourSummaryView(APIView):
    """
    Get summary statistics for wage hour analysis.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdmin]

    @swagger_auto_schema(
        operation_description="Get wage hour analysis summary statistics",
        tags=["Labor Employment - Analytics"],
        manual_parameters=[
            openapi.Parameter('comm_run_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={200: WageHourSummarySerializer}
    )
    def get(self, request):
        """Get wage hour analysis summary statistics"""
        comm_run_id = request.query_params.get('comm_run_id')
        if not comm_run_id:
            return Response({"error": "comm_run_id parameter is required"},
                          status=status.HTTP_400_BAD_REQUEST)

        # Ensure user owns the communications run
        comm_run = get_object_or_404(WorkplaceCommunicationsRun, pk=comm_run_id, run__user=request.user)

        # Get wage hour analysis summary
        analyses = WageHourAnalysis.objects.filter(
            communications_run=comm_run,
            user=request.user
        )

        summary_data = {
            'total_employees_analyzed': analyses.count(),
            'total_overtime_hours': analyses.aggregate(Sum('overtime_hours'))['overtime_hours__sum'] or 0.0,
            'potential_violations_count': analyses.filter(
                Q(potential_overtime_violations=True) |
                Q(potential_break_violations=True) |
                Q(potential_meal_violations=True)
            ).count(),
            'total_unpaid_overtime': analyses.aggregate(Sum('overtime_pay'))['overtime_pay__sum'] or 0.0,
            'avg_weekly_hours': analyses.aggregate(Avg('total_hours_worked'))['total_hours_worked__avg'] or 0.0,
        }

        serializer = WageHourSummarySerializer(summary_data)
        return Response(serializer.data)
