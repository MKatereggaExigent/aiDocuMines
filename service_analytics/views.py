import logging
from datetime import datetime, timedelta
from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from oauth2_provider.contrib.rest_framework import OAuth2Authentication, TokenHasReadWriteScope
from custom_authentication.permissions import IsClientOrAdminOrSuperUser
from oauth2_provider.models import Application
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

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
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdminOrSuperUser]

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
    permission_classes = [TokenHasReadWriteScope, IsClientOrAdminOrSuperUser]

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

