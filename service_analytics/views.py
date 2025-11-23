import logging
from datetime import datetime, timedelta
from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from oauth2_provider.contrib.rest_framework import OAuth2Authentication, TokenHasReadWriteScope
from oauth2_provider.models import Application
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Import Client model
from custom_authentication.models import Client

# Import ServiceExecution models from all 5 vertical apps
from private_equity.models import ServiceExecution as PEServiceExecution
from class_actions.models import ServiceExecution as CAServiceExecution
from labor_employment.models import ServiceExecution as LEServiceExecution
from ip_litigation.models import ServiceExecution as IPServiceExecution
from regulatory_compliance.models import ServiceExecution as RCServiceExecution

from service_analytics.serializers import (
    OverviewSerializer,
    ServiceExecutionSerializer,
    ServiceBreakdownSerializer,
    TrendsSerializer,
)

logger = logging.getLogger(__name__)

# Swagger Parameters
client_id_param = openapi.Parameter("X-Client-ID", openapi.IN_HEADER, type=openapi.TYPE_STRING, required=True)
client_secret_param = openapi.Parameter("X-Client-Secret", openapi.IN_HEADER, type=openapi.TYPE_STRING, required=True)


def get_user_from_client_id(client_id):
    """Get user from OAuth2 client_id"""
    try:
        application = Application.objects.get(client_id=client_id)
        return application.user
    except Application.DoesNotExist:
        return None


class ServiceAnalyticsOverviewAPIView(APIView):
    """
    Get overall service analytics overview across all 5 legal verticals.
    Returns aggregated statistics including total executions, success rates, and breakdowns.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope]

    @swagger_auto_schema(
        manual_parameters=[client_id_param, client_secret_param],
        operation_description="Get overall service analytics overview across all legal verticals",
        responses={200: OverviewSerializer()}
    )
    def get(self, request):
        client_id = request.headers.get("X-Client-ID")
        client_secret = request.headers.get("X-Client-Secret")

        if not all([client_id, client_secret]):
            return Response(
                {"error": "Missing X-Client-ID or X-Client-Secret headers"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = get_user_from_client_id(client_id)
        if not user:
            return Response(
                {"error": "Invalid client credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Get all service executions for this user from all 5 verticals
        pe_executions = PEServiceExecution.objects.filter(user=user)
        ca_executions = CAServiceExecution.objects.filter(user=user)
        le_executions = LEServiceExecution.objects.filter(user=user)
        ip_executions = IPServiceExecution.objects.filter(user=user)
        rc_executions = RCServiceExecution.objects.filter(user=user)

        # Calculate overall statistics
        total_executions = (
            pe_executions.count() +
            ca_executions.count() +
            le_executions.count() +
            ip_executions.count() +
            rc_executions.count()
        )

        # Status counts
        completed = (
            pe_executions.filter(status='completed').count() +
            ca_executions.filter(status='completed').count() +
            le_executions.filter(status='completed').count() +
            ip_executions.filter(status='completed').count() +
            rc_executions.filter(status='completed').count()
        )

        failed = (
            pe_executions.filter(status='failed').count() +
            ca_executions.filter(status='failed').count() +
            le_executions.filter(status='failed').count() +
            ip_executions.filter(status='failed').count() +
            rc_executions.filter(status='failed').count()
        )

        running = (
            pe_executions.filter(status='running').count() +
            ca_executions.filter(status='running').count() +
            le_executions.filter(status='running').count() +
            ip_executions.filter(status='running').count() +
            rc_executions.filter(status='running').count()
        )

        pending = (
            pe_executions.filter(status='pending').count() +
            ca_executions.filter(status='pending').count() +
            le_executions.filter(status='pending').count() +
            ip_executions.filter(status='pending').count() +
            rc_executions.filter(status='pending').count()
        )

        cancelled = (
            pe_executions.filter(status='cancelled').count() +
            ca_executions.filter(status='cancelled').count() +
            le_executions.filter(status='cancelled').count() +
            ip_executions.filter(status='cancelled').count() +
            rc_executions.filter(status='cancelled').count()
        )

        # Success rate
        success_rate = (completed / total_executions * 100) if total_executions > 0 else 0

        # Total output files
        total_output_files = (
            pe_executions.aggregate(total=Sum('output_count'))['total'] or 0
        ) + (
            ca_executions.aggregate(total=Sum('output_count'))['total'] or 0
        ) + (
            le_executions.aggregate(total=Sum('output_count'))['total'] or 0
        ) + (
            ip_executions.aggregate(total=Sum('output_count'))['total'] or 0
        ) + (
            rc_executions.aggregate(total=Sum('output_count'))['total'] or 0
        )

        # Average execution time (only for completed executions)
        pe_avg = pe_executions.filter(status='completed', execution_time_seconds__isnull=False).aggregate(avg=Avg('execution_time_seconds'))['avg']
        ca_avg = ca_executions.filter(status='completed', execution_time_seconds__isnull=False).aggregate(avg=Avg('execution_time_seconds'))['avg']
        le_avg = le_executions.filter(status='completed', execution_time_seconds__isnull=False).aggregate(avg=Avg('execution_time_seconds'))['avg']
        ip_avg = ip_executions.filter(status='completed', execution_time_seconds__isnull=False).aggregate(avg=Avg('execution_time_seconds'))['avg']
        rc_avg = rc_executions.filter(status='completed', execution_time_seconds__isnull=False).aggregate(avg=Avg('execution_time_seconds'))['avg']

        # Calculate weighted average
        avg_times = [t for t in [pe_avg, ca_avg, le_avg, ip_avg, rc_avg] if t is not None]
        avg_execution_time = sum(avg_times) / len(avg_times) if avg_times else None

        # Verticals breakdown
        verticals_breakdown = []

        # Private Equity
        pe_total = pe_executions.count()
        if pe_total > 0:
            pe_completed = pe_executions.filter(status='completed').count()
            verticals_breakdown.append({
                'vertical': 'Private Equity',
                'total_executions': pe_total,
                'completed': pe_completed,
                'failed': pe_executions.filter(status='failed').count(),
                'running': pe_executions.filter(status='running').count(),
                'pending': pe_executions.filter(status='pending').count(),
                'success_rate': (pe_completed / pe_total * 100) if pe_total > 0 else 0,
                'avg_execution_time': pe_avg
            })

        # Class Actions
        ca_total = ca_executions.count()
        if ca_total > 0:
            ca_completed = ca_executions.filter(status='completed').count()
            verticals_breakdown.append({
                'vertical': 'Class Actions',
                'total_executions': ca_total,
                'completed': ca_completed,
                'failed': ca_executions.filter(status='failed').count(),
                'running': ca_executions.filter(status='running').count(),
                'pending': ca_executions.filter(status='pending').count(),
                'success_rate': (ca_completed / ca_total * 100) if ca_total > 0 else 0,
                'avg_execution_time': ca_avg
            })

        # Labor Employment
        le_total = le_executions.count()
        if le_total > 0:
            le_completed = le_executions.filter(status='completed').count()
            verticals_breakdown.append({
                'vertical': 'Labor Employment',
                'total_executions': le_total,
                'completed': le_completed,
                'failed': le_executions.filter(status='failed').count(),
                'running': le_executions.filter(status='running').count(),
                'pending': le_executions.filter(status='pending').count(),
                'success_rate': (le_completed / le_total * 100) if le_total > 0 else 0,
                'avg_execution_time': le_avg
            })

        # IP Litigation
        ip_total = ip_executions.count()
        if ip_total > 0:
            ip_completed = ip_executions.filter(status='completed').count()
            verticals_breakdown.append({
                'vertical': 'IP Litigation',
                'total_executions': ip_total,
                'completed': ip_completed,
                'failed': ip_executions.filter(status='failed').count(),
                'running': ip_executions.filter(status='running').count(),
                'pending': ip_executions.filter(status='pending').count(),
                'success_rate': (ip_completed / ip_total * 100) if ip_total > 0 else 0,
                'avg_execution_time': ip_avg
            })

        # Regulatory Compliance
        rc_total = rc_executions.count()
        if rc_total > 0:
            rc_completed = rc_executions.filter(status='completed').count()
            verticals_breakdown.append({
                'vertical': 'Regulatory Compliance',
                'total_executions': rc_total,
                'completed': rc_completed,
                'failed': rc_executions.filter(status='failed').count(),
                'running': rc_executions.filter(status='running').count(),
                'pending': rc_executions.filter(status='pending').count(),
                'success_rate': (rc_completed / rc_total * 100) if rc_total > 0 else 0,
                'avg_execution_time': rc_avg
            })

        # Most used services (top 10)
        most_used_services = self._get_most_used_services(user)

        response_data = {
            'total_executions': total_executions,
            'completed': completed,
            'failed': failed,
            'running': running,
            'pending': pending,
            'cancelled': cancelled,
            'success_rate': round(success_rate, 2),
            'total_output_files': total_output_files,
            'avg_execution_time': round(avg_execution_time, 2) if avg_execution_time else None,
            'verticals_breakdown': verticals_breakdown,
            'most_used_services': most_used_services[:10]
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def _get_most_used_services(self, user):
        """Get most used services across all verticals"""
        services = []

        # Private Equity services
        pe_services = PEServiceExecution.objects.filter(user=user).values('service_type', 'service_name').annotate(
            count=Count('id'),
            completed_count=Count('id', filter=Q(status='completed'))
        ).order_by('-count')

        for service in pe_services:
            services.append({
                'service_type': service['service_type'],
                'service_name': service['service_name'],
                'vertical': 'Private Equity',
                'count': service['count'],
                'success_rate': (service['completed_count'] / service['count'] * 100) if service['count'] > 0 else 0,
                'avg_execution_time': None  # Can be calculated if needed
            })

        # Class Actions services
        ca_services = CAServiceExecution.objects.filter(user=user).values('service_type', 'service_name').annotate(
            count=Count('id'),
            completed_count=Count('id', filter=Q(status='completed'))
        ).order_by('-count')

        for service in ca_services:
            services.append({
                'service_type': service['service_type'],
                'service_name': service['service_name'],
                'vertical': 'Class Actions',
                'count': service['count'],
                'success_rate': (service['completed_count'] / service['count'] * 100) if service['count'] > 0 else 0,
                'avg_execution_time': None
            })

        # Labor Employment services
        le_services = LEServiceExecution.objects.filter(user=user).values('service_type', 'service_name').annotate(
            count=Count('id'),
            completed_count=Count('id', filter=Q(status='completed'))
        ).order_by('-count')

        for service in le_services:
            services.append({
                'service_type': service['service_type'],
                'service_name': service['service_name'],
                'vertical': 'Labor Employment',
                'count': service['count'],
                'success_rate': (service['completed_count'] / service['count'] * 100) if service['count'] > 0 else 0,
                'avg_execution_time': None
            })

        # IP Litigation services
        ip_services = IPServiceExecution.objects.filter(user=user).values('service_type', 'service_name').annotate(
            count=Count('id'),
            completed_count=Count('id', filter=Q(status='completed'))
        ).order_by('-count')

        for service in ip_services:
            services.append({
                'service_type': service['service_type'],
                'service_name': service['service_name'],
                'vertical': 'IP Litigation',
                'count': service['count'],
                'success_rate': (service['completed_count'] / service['count'] * 100) if service['count'] > 0 else 0,
                'avg_execution_time': None
            })

        # Regulatory Compliance services
        rc_services = RCServiceExecution.objects.filter(user=user).values('service_type', 'service_name').annotate(
            count=Count('id'),
            completed_count=Count('id', filter=Q(status='completed'))
        ).order_by('-count')

        for service in rc_services:
            services.append({
                'service_type': service['service_type'],
                'service_name': service['service_name'],
                'vertical': 'Regulatory Compliance',
                'count': service['count'],
                'success_rate': (service['completed_count'] / service['count'] * 100) if service['count'] > 0 else 0,
                'avg_execution_time': None
            })

        # Sort by count and return
        services.sort(key=lambda x: x['count'], reverse=True)
        return services


class RecentActivityAPIView(APIView):
    """
    Get recent service execution activity across all verticals.
    Returns the last 20 service executions.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope]

    @swagger_auto_schema(
        manual_parameters=[
            client_id_param,
            client_secret_param,
            openapi.Parameter("limit", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False, description="Number of records to return (default: 20)")
        ],
        operation_description="Get recent service execution activity",
        responses={200: ServiceExecutionSerializer(many=True)}
    )
    def get(self, request):
        client_id = request.headers.get("X-Client-ID")
        client_secret = request.headers.get("X-Client-Secret")
        limit = int(request.query_params.get("limit", 20))

        if not all([client_id, client_secret]):
            return Response(
                {"error": "Missing X-Client-ID or X-Client-Secret headers"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = get_user_from_client_id(client_id)
        if not user:
            return Response(
                {"error": "Invalid client credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Get recent executions from all verticals
        recent_executions = []

        # Private Equity
        pe_executions = PEServiceExecution.objects.filter(user=user).order_by('-started_at')[:limit]
        for exec in pe_executions:
            recent_executions.append({
                'id': exec.id,
                'vertical': 'Private Equity',
                'service_type': exec.service_type,
                'service_name': exec.service_name,
                'status': exec.status,
                'started_at': exec.started_at,
                'completed_at': exec.completed_at,
                'execution_time_seconds': exec.execution_time_seconds,
                'output_count': exec.output_count,
                'output_type': exec.output_type,
                'error_message': exec.error_message
            })

        # Class Actions
        ca_executions = CAServiceExecution.objects.filter(user=user).order_by('-started_at')[:limit]
        for exec in ca_executions:
            recent_executions.append({
                'id': exec.id,
                'vertical': 'Class Actions',
                'service_type': exec.service_type,
                'service_name': exec.service_name,
                'status': exec.status,
                'started_at': exec.started_at,
                'completed_at': exec.completed_at,
                'execution_time_seconds': exec.execution_time_seconds,
                'output_count': exec.output_count,
                'output_type': exec.output_type,
                'error_message': exec.error_message
            })

        # Labor Employment
        le_executions = LEServiceExecution.objects.filter(user=user).order_by('-started_at')[:limit]
        for exec in le_executions:
            recent_executions.append({
                'id': exec.id,
                'vertical': 'Labor Employment',
                'service_type': exec.service_type,
                'service_name': exec.service_name,
                'status': exec.status,
                'started_at': exec.started_at,
                'completed_at': exec.completed_at,
                'execution_time_seconds': exec.execution_time_seconds,
                'output_count': exec.output_count,
                'output_type': exec.output_type,
                'error_message': exec.error_message
            })

        # IP Litigation
        ip_executions = IPServiceExecution.objects.filter(user=user).order_by('-started_at')[:limit]
        for exec in ip_executions:
            recent_executions.append({
                'id': exec.id,
                'vertical': 'IP Litigation',
                'service_type': exec.service_type,
                'service_name': exec.service_name,
                'status': exec.status,
                'started_at': exec.started_at,
                'completed_at': exec.completed_at,
                'execution_time_seconds': exec.execution_time_seconds,
                'output_count': exec.output_count,
                'output_type': exec.output_type,
                'error_message': exec.error_message
            })

        # Regulatory Compliance
        rc_executions = RCServiceExecution.objects.filter(user=user).order_by('-started_at')[:limit]
        for exec in rc_executions:
            recent_executions.append({
                'id': exec.id,
                'vertical': 'Regulatory Compliance',
                'service_type': exec.service_type,
                'service_name': exec.service_name,
                'status': exec.status,
                'started_at': exec.started_at,
                'completed_at': exec.completed_at,
                'execution_time_seconds': exec.execution_time_seconds,
                'output_count': exec.output_count,
                'output_type': exec.output_type,
                'error_message': exec.error_message
            })

        # Sort by started_at and limit
        recent_executions.sort(key=lambda x: x['started_at'], reverse=True)
        recent_executions = recent_executions[:limit]

        return Response(recent_executions, status=status.HTTP_200_OK)


class CreateServiceExecutionView(APIView):
    """
    POST /api/v1/service-analytics/executions/create/

    Creates a service execution record for any of the 5 legal verticals.
    This is a universal endpoint that routes to the appropriate vertical's ServiceExecution model.

    Request Body:
    {
        "vertical": "class_actions",  // One of: private_equity, class_actions, labor_employment, ip_litigation, regulatory_compliance
        "run_id": "uuid",  // The run ID for the vertical (e.g., mass_claims_run_id, due_diligence_run_id, etc.)
        "service_type": "ca-intake-triage",
        "service_name": "Process and triage intake forms",
        "service_version": "1.0",
        "input_file_ids": [1, 2, 3],  // Optional: List of File IDs
        "input_parameters": {...},  // Optional: Service parameters
        "output_file_ids": [4, 5],  // Optional: List of output File IDs
        "output_type": "report",  // One of: json, pdf, excel, html, text, report
        "output_count": 2,
        "execution_time_seconds": 45,
        "status": "completed",  // One of: pending, running, completed, failed, cancelled
        "error_message": "",  // Optional: Error message if failed
        "execution_metadata": {...}  // Optional: Additional metadata
    }

    Response:
    {
        "success": true,
        "data": {
            "id": "uuid",
            "vertical": "class_actions",
            "service_type": "ca-intake-triage",
            "service_name": "Process and triage intake forms",
            "status": "completed",
            "started_at": "2024-11-22T14:30:22Z"
        }
    }
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope]

    @swagger_auto_schema(
        operation_description="Create a service execution record for any legal vertical",
        manual_parameters=[client_id_param, client_secret_param],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['vertical', 'run_id', 'service_type', 'service_name'],
            properties={
                'vertical': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['private_equity', 'class_actions', 'labor_employment', 'ip_litigation', 'regulatory_compliance'],
                    description='Legal vertical'
                ),
                'run_id': openapi.Schema(type=openapi.TYPE_STRING, description='Run ID for the vertical'),
                'service_type': openapi.Schema(type=openapi.TYPE_STRING, description='Service type code'),
                'service_name': openapi.Schema(type=openapi.TYPE_STRING, description='Human-readable service name'),
                'service_version': openapi.Schema(type=openapi.TYPE_STRING, description='Service version (default: 1.0)'),
                'input_file_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER), description='List of input file IDs'),
                'input_parameters': openapi.Schema(type=openapi.TYPE_OBJECT, description='Service input parameters'),
                'output_file_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER), description='List of output file IDs'),
                'output_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['json', 'pdf', 'excel', 'html', 'text', 'report'], description='Output type'),
                'output_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of output files'),
                'execution_time_seconds': openapi.Schema(type=openapi.TYPE_INTEGER, description='Execution time in seconds'),
                'status': openapi.Schema(type=openapi.TYPE_STRING, enum=['pending', 'running', 'completed', 'failed', 'cancelled'], description='Execution status'),
                'error_message': openapi.Schema(type=openapi.TYPE_STRING, description='Error message if failed'),
                'execution_metadata': openapi.Schema(type=openapi.TYPE_OBJECT, description='Additional metadata'),
            }
        ),
        responses={
            201: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_STRING),
                            'vertical': openapi.Schema(type=openapi.TYPE_STRING),
                            'service_type': openapi.Schema(type=openapi.TYPE_STRING),
                            'service_name': openapi.Schema(type=openapi.TYPE_STRING),
                            'status': openapi.Schema(type=openapi.TYPE_STRING),
                            'started_at': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                }
            ),
            400: "Bad Request - Missing required fields or invalid vertical",
            404: "Run not found"
        }
    )
    def post(self, request):
        try:
            # Get client and user from OAuth2
            client_id = request.data.get('client_id') or request.query_params.get('client_id')
            client_secret = request.data.get('client_secret') or request.query_params.get('client_secret')

            if not client_id or not client_secret:
                return Response({
                    'success': False,
                    'error': 'Missing client_id or client_secret'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                client = Client.objects.get(client_id=client_id, client_secret=client_secret)
            except Client.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Invalid client credentials'
                }, status=status.HTTP_401_UNAUTHORIZED)

            user = request.user

            # Extract request data
            vertical = request.data.get('vertical')
            run_id = request.data.get('run_id')
            service_type = request.data.get('service_type')
            service_name = request.data.get('service_name')
            service_version = request.data.get('service_version', '1.0')
            input_file_ids = request.data.get('input_file_ids', [])
            input_parameters = request.data.get('input_parameters', {})
            output_file_ids = request.data.get('output_file_ids', [])
            output_type = request.data.get('output_type', 'json')
            output_count = request.data.get('output_count', 0)
            execution_time_seconds = request.data.get('execution_time_seconds')
            exec_status = request.data.get('status', 'pending')
            error_message = request.data.get('error_message', '')
            execution_metadata = request.data.get('execution_metadata', {})

            # Validate required fields
            if not vertical or not run_id or not service_type or not service_name:
                return Response({
                    'success': False,
                    'error': 'Missing required fields: vertical, run_id, service_type, service_name'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Route to appropriate vertical
            execution = None

            if vertical == 'private_equity':
                from private_equity.models import DueDiligenceRun
                try:
                    run = DueDiligenceRun.objects.get(id=run_id, client=client)
                except DueDiligenceRun.DoesNotExist:
                    return Response({
                        'success': False,
                        'error': f'DueDiligenceRun with ID {run_id} not found'
                    }, status=status.HTTP_404_NOT_FOUND)

                execution = PEServiceExecution.objects.create(
                    client=client,
                    user=user,
                    due_diligence_run=run,
                    service_type=service_type,
                    service_name=service_name,
                    service_version=service_version,
                    status=exec_status,
                    input_parameters=input_parameters,
                    output_type=output_type,
                    output_count=output_count,
                    execution_time_seconds=execution_time_seconds,
                    error_message=error_message,
                    execution_metadata=execution_metadata
                )

            elif vertical == 'class_actions':
                from class_actions.models import MassClaimsRun
                try:
                    run = MassClaimsRun.objects.get(id=run_id, client=client)
                except MassClaimsRun.DoesNotExist:
                    return Response({
                        'success': False,
                        'error': f'MassClaimsRun with ID {run_id} not found'
                    }, status=status.HTTP_404_NOT_FOUND)

                execution = CAServiceExecution.objects.create(
                    client=client,
                    user=user,
                    mass_claims_run=run,
                    service_type=service_type,
                    service_name=service_name,
                    service_version=service_version,
                    status=exec_status,
                    input_parameters=input_parameters,
                    output_type=output_type,
                    output_count=output_count,
                    execution_time_seconds=execution_time_seconds,
                    error_message=error_message,
                    execution_metadata=execution_metadata
                )

            elif vertical == 'labor_employment':
                from labor_employment.models import WorkplaceCommunicationsRun
                try:
                    run = WorkplaceCommunicationsRun.objects.get(id=run_id, client=client)
                except WorkplaceCommunicationsRun.DoesNotExist:
                    return Response({
                        'success': False,
                        'error': f'WorkplaceCommunicationsRun with ID {run_id} not found'
                    }, status=status.HTTP_404_NOT_FOUND)

                execution = LEServiceExecution.objects.create(
                    client=client,
                    user=user,
                    workplace_communications_run=run,
                    service_type=service_type,
                    service_name=service_name,
                    service_version=service_version,
                    status=exec_status,
                    input_parameters=input_parameters,
                    output_type=output_type,
                    output_count=output_count,
                    execution_time_seconds=execution_time_seconds,
                    error_message=error_message,
                    execution_metadata=execution_metadata
                )

            elif vertical == 'ip_litigation':
                from ip_litigation.models import PatentAnalysisRun
                try:
                    run = PatentAnalysisRun.objects.get(id=run_id, client=client)
                except PatentAnalysisRun.DoesNotExist:
                    return Response({
                        'success': False,
                        'error': f'PatentAnalysisRun with ID {run_id} not found'
                    }, status=status.HTTP_404_NOT_FOUND)

                execution = IPServiceExecution.objects.create(
                    client=client,
                    user=user,
                    patent_analysis_run=run,
                    service_type=service_type,
                    service_name=service_name,
                    service_version=service_version,
                    status=exec_status,
                    input_parameters=input_parameters,
                    output_type=output_type,
                    output_count=output_count,
                    execution_time_seconds=execution_time_seconds,
                    error_message=error_message,
                    execution_metadata=execution_metadata
                )

            elif vertical == 'regulatory_compliance':
                from regulatory_compliance.models import ComplianceAuditRun
                try:
                    run = ComplianceAuditRun.objects.get(id=run_id, client=client)
                except ComplianceAuditRun.DoesNotExist:
                    return Response({
                        'success': False,
                        'error': f'ComplianceAuditRun with ID {run_id} not found'
                    }, status=status.HTTP_404_NOT_FOUND)

                execution = RCServiceExecution.objects.create(
                    client=client,
                    user=user,
                    compliance_audit_run=run,
                    service_type=service_type,
                    service_name=service_name,
                    service_version=service_version,
                    status=exec_status,
                    input_parameters=input_parameters,
                    output_type=output_type,
                    output_count=output_count,
                    execution_time_seconds=execution_time_seconds,
                    error_message=error_message,
                    execution_metadata=execution_metadata
                )
            else:
                return Response({
                    'success': False,
                    'error': f'Invalid vertical: {vertical}. Must be one of: private_equity, class_actions, labor_employment, ip_litigation, regulatory_compliance'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Add input files if provided
            if input_file_ids:
                from core.models import File
                input_files = File.objects.filter(id__in=input_file_ids)
                execution.input_files.set(input_files)

            # Return response
            return Response({
                'success': True,
                'data': {
                    'id': str(execution.id),
                    'vertical': vertical,
                    'service_type': execution.service_type,
                    'service_name': execution.service_name,
                    'status': execution.status,
                    'started_at': execution.started_at.isoformat()
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating service execution: {str(e)}")
            logger.error(traceback.format_exc())
            return Response({
                'success': False,
                'error': f'Failed to create service execution: {str(e)}',
                'traceback': traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

