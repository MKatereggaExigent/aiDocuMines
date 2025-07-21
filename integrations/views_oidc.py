# integrations/views_oidc.py (OIDC callback using .env-based superuser secrets path)

import os
import json
import requests
from django.conf import settings
from django.shortcuts import redirect
from django.views import View
from django.http import HttpResponseBadRequest, HttpResponseServerError
from integrations.utils import STATE_REGISTRY, NONCE_REGISTRY
from integrations.models import IntegrationLog

SUPERUSER_SECRET_PATH = os.getenv("SUPERUSER_SECRET_PATH", "")

def load_superuser_secrets():
    try:
        with open(SUPERUSER_SECRET_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load superuser secrets: {e}")


class OIDCCallbackView(View):
    def get(self, request):
        user = request.user if request.user.is_authenticated else None
        code = request.GET.get("code")
        state = request.GET.get("state")

        if not code or not state:
            return HttpResponseBadRequest("Missing `code` or `state` parameter.")

        # Verify state
        user_id = user.id if user else None
        if user_id not in STATE_REGISTRY or STATE_REGISTRY[user_id] != state:
            IntegrationLog.objects.create(
                user=user,
                connector="nextcloud",
                status="error",
                details=f"OIDC state mismatch or expired."
            )
            return HttpResponseBadRequest("Invalid or expired state.")

        # Prepare token exchange request
        try:
            secrets = load_superuser_secrets()

            token_url = "https://aidocumines-api-layer.aidocumines.com/o/token/"
            redirect_uri = "https://nextcloud.aidocumines.com/apps/user_oidc/code"
            client_id = secrets.get("client_id")
            client_secret = secrets.get("client_secret")

            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            }

            response = requests.post(token_url, data=data)
            token_data = response.json()

            if "id_token" not in token_data:
                raise ValueError(f"ID token missing from response: {token_data}")

            IntegrationLog.objects.create(
                user=user,
                connector="nextcloud",
                status="success",
                details="OIDC callback successful, ID token retrieved."
            )

            return redirect("https://nextcloud.aidocumines.com")

        except Exception as e:
            IntegrationLog.objects.create(
                user=user,
                connector="nextcloud",
                status="error",
                details=f"OIDC callback processing failed: {str(e)}"
            )
            return HttpResponseServerError("OIDC callback failed.")

