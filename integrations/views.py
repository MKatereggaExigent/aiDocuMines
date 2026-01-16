# integrations/views.py

import secrets
from django.views import View
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseServerError

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework import status, generics, filters
from custom_authentication.permissions import IsClientOrAdminOrSuperUser

from integrations.oidc_utils import get_or_create_nextcloud_oidc_user, generate_nextcloud_oidc_url
from integrations.tasks import generate_nextcloud_url_async, sync_user_to_nextcloud_host
from integrations.models import IntegrationLog
from .serializers import IntegrationLogSerializer

from integrations.registry import STATE_REGISTRY, NONCE_REGISTRY


class NextcloudRedirectView(LoginRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request):
        user = request.user
        try:
            state = secrets.token_urlsafe(16)
            nonce = secrets.token_urlsafe(16)

            STATE_REGISTRY[user.id] = state
            NONCE_REGISTRY[user.id] = nonce

            url = generate_nextcloud_oidc_url(user, state=state, nonce=nonce)
            return redirect(url)

        except Exception as e:
            IntegrationLog.objects.create(
                user=user,
                connector="nextcloud",
                status="error",
                details=f"Redirect error: {str(e)}"
            )
            return HttpResponseServerError(f"Nextcloud autologin failed: {str(e)}")


class NextcloudAutologinView(APIView):
    permission_classes = [IsAuthenticated, IsClientOrAdminOrSuperUser]

    def get(self, request):
        user = request.user
        try:
            get_or_create_nextcloud_oidc_user(user)

            state = secrets.token_urlsafe(16)
            nonce = secrets.token_urlsafe(16)

            STATE_REGISTRY[user.id] = state
            NONCE_REGISTRY[user.id] = nonce

            url = generate_nextcloud_oidc_url(user, state=state, nonce=nonce)
            return Response({"nextcloud_url": url})

        except Exception as e:
            IntegrationLog.objects.create(
                user=user,
                connector="nextcloud",
                status="processing",
                details=f"Nextcloud OIDC fallback triggered for {user.id}: {str(e)}"
            )

            generate_nextcloud_url_async.delay(user.id)
            sync_user_to_nextcloud_host.delay(user.id, user.username)

            return Response({
                "message": "We’re setting up your Nextcloud account.",
                "error": str(e)
            }, status=status.HTTP_202_ACCEPTED)


class IntegrationLogListView(generics.ListAPIView):
    queryset = IntegrationLog.objects.select_related('user').order_by('-timestamp')
    serializer_class = IntegrationLogSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__email', 'user__username', 'connector', 'status', 'details']
    ordering_fields = ['timestamp', 'status', 'connector']


class CustomOIDCMetadataView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        base_url = "https://aidocumines-api-layer.aidocumines.com/o"
        return Response({
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/authorize/",
            "token_endpoint": f"{base_url}/token/",
            "userinfo_endpoint": f"{base_url}/userinfo/",
            "jwks_uri": f"{base_url}/.well-known/jwks.json",
            "scopes_supported": ["openid", "profile", "email", "read", "write"],
            "response_types_supported": [
                "code", "token", "id_token", "id_token token",
                "code token", "code id_token", "code id_token token"
            ],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256", "HS256"],
            "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
            "code_challenge_methods_supported": ["plain", "S256"],
            "claims_supported": ["sub"]
        })

