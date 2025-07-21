# integrations/urls.py

from django.urls import path
from .views import (
    NextcloudAutologinView,
    NextcloudRedirectView,
    IntegrationLogListView,
    CustomOIDCMetadataView
)
from .views_oidc import OIDCCallbackView
from .utils import STATE_REGISTRY, NONCE_REGISTRY  # Keep for reference if needed in future views

app_name = "integrations"

urlpatterns = [
    # API: Trigger autologin or async provisioning for current user
    path("nextcloud-autologin/", NextcloudAutologinView.as_view(), name="nextcloud-autologin"),

    # Web redirect: For direct browser-based login
    path("nextcloud-redirect/", NextcloudRedirectView.as_view(), name="nextcloud-redirect"),

    # Admin: List integration logs
    path("logs/", IntegrationLogListView.as_view(), name="integration-log-list"),

    # OpenID Connect Metadata endpoint
    path(".well-known/openid-configuration", CustomOIDCMetadataView.as_view(), name="oidc-metadata"),

    # OpenID Connect Callback handler
    path("oidc/callback/", OIDCCallbackView.as_view(), name="oidc-callback"),
]

