# integrations/views.py

from django.views import View
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseServerError

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from integrations.utils import generate_nextcloud_autologin_url
from integrations.tasks import generate_nextcloud_url_async
from integrations.models import IntegrationLog

from rest_framework import generics, filters
from rest_framework.permissions import IsAdminUser
from .serializers import IntegrationLogSerializer


def _get_nextcloud_url_for_user(user):
    """
    Shared logic to generate the Nextcloud autologin URL.
    Raises Exception if failed.
    """
    return generate_nextcloud_autologin_url(user)


class NextcloudRedirectView(LoginRequiredMixin, View):
    """
    Web-based view to redirect to the autologin Nextcloud URL.
    """
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request):
        user = request.user
        try:
            nextcloud_url = _get_nextcloud_url_for_user(user)
            return redirect(nextcloud_url)
        except Exception as e:
            IntegrationLog.objects.create(
                user=user,
                connector="nextcloud",
                status="error",
                details=f"Redirect error: {str(e)}"
            )
            return HttpResponseServerError(f"Nextcloud autologin failed: {str(e)}")


class NextcloudAutologinView(APIView):
    """
    API-based view to fetch the autologin Nextcloud URL.
    Returns JSON response with the link or error.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            # Try to generate the autologin URL immediately
            nextcloud_url = _get_nextcloud_url_for_user(user)
            return Response({"nextcloud_url": nextcloud_url}, status=status.HTTP_200_OK)
        except Exception as e:
            # If failed, log the error and trigger the async task for processing
            IntegrationLog.objects.create(
                user=user,
                connector="nextcloud",
                status="processing",
                details=f"Processing Nextcloud account for user {user.id}: {str(e)}"
            )
            # Trigger the async task to process Nextcloud provisioning
            generate_nextcloud_url_async.delay(user.id)

            return Response({
                "error": str(e),
                "message": "We’re processing your Nextcloud account. Try again shortly."
            }, status=status.HTTP_202_ACCEPTED)


class IntegrationLogListView(generics.ListAPIView):
    queryset = IntegrationLog.objects.select_related('user').order_by('-timestamp')
    serializer_class = IntegrationLogSerializer
    permission_classes = [IsAdminUser]  # Or use a custom permission
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__email', 'user__username', 'connector', 'status', 'details']
    ordering_fields = ['timestamp', 'status', 'connector']

