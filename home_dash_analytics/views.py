from __future__ import annotations

import logging
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from oauth2_provider.contrib.rest_framework import (
    OAuth2Authentication,
    TokenHasReadWriteScope,
)

from .utils import (
    build_overview,
    SECTIONS,
    build_cards,
    build_timeseries,
    build_top_files,
    build_top_searches,
)
from .models import HomeAnalyticsSnapshot

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Health (no auth)
# ──────────────────────────────────────────────────────────────────────────────
@csrf_exempt
def health(request):
    return JsonResponse({"status": "ok"})


# ──────────────────────────────────────────────────────────────────────────────
# Swagger parameters
# ──────────────────────────────────────────────────────────────────────────────
client_id_param = openapi.Parameter(
    "X-Client-ID",
    openapi.IN_HEADER,
    type=openapi.TYPE_STRING,
    required=False,  # optional; we bind to token's user; if provided, we verify it
    description="(Optional) OAuth2 client_id. If provided, it must match the client that issued the access token.",
)

project_id_param = openapi.Parameter(
    "project_id",
    openapi.IN_QUERY,
    type=openapi.TYPE_STRING,
    required=False,
    description="Optional filter: project_id",
)

service_id_param = openapi.Parameter(
    "service_id",
    openapi.IN_QUERY,
    type=openapi.TYPE_STRING,
    required=False,
    description="Optional filter: service_id",
)

since_param = openapi.Parameter(
    "since",
    openapi.IN_QUERY,
    type=openapi.TYPE_STRING,
    required=False,
    description="Optional ISO8601 timestamp (e.g. 2025-08-01T00:00:00Z) to window certain metrics.",
)

range_param = openapi.Parameter(
    "range",
    openapi.IN_QUERY,
    type=openapi.TYPE_STRING,
    required=False,
    description="Time range like '30d' for time series",
)

from_param = openapi.Parameter(
    "from",
    openapi.IN_QUERY,
    type=openapi.TYPE_STRING,
    required=False,
    description="YYYY-MM-DD",
)

to_param = openapi.Parameter(
    "to",
    openapi.IN_QUERY,
    type=openapi.TYPE_STRING,
    required=False,
    description="YYYY-MM-DD",
)


# ──────────────────────────────────────────────────────────────────────────────
# Auth base view: bind to token user and (optionally) verify client header
# ──────────────────────────────────────────────────────────────────────────────
class OAuth2SecuredAPIView(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope]  # requires 'read' or 'write' scope

    def _get_user(self, request):
        """
        Primary binding: request.user from access token (subject).
        Optional: if X-Client-ID header is present, verify it matches token.application.
        Fallback: for client-credentials tokens (no user), use application.user if present.
        """
        hdr_cid = request.headers.get("X-Client-ID")
        token = getattr(request, "auth", None)
        token_app = getattr(token, "application", None)

        # 1) Normal user-bound tokens
        if getattr(request, "user", None) and request.user.is_authenticated:
            if hdr_cid and token_app and getattr(token_app, "client_id", None) != hdr_cid:
                return None, Response(
                    {"error": "X-Client-ID does not match access token’s client"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return request.user, None

        # 2) Client-credentials tokens (no user on token)
        if token_app and getattr(token_app, "user", None):
            if hdr_cid and getattr(token_app, "client_id", None) != hdr_cid:
                return None, Response(
                    {"error": "X-Client-ID does not match access token’s client"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return token_app.user, None

        return None, Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)


# ──────────────────────────────────────────────────────────────────────────────
# Views
# ──────────────────────────────────────────────────────────────────────────────
@method_decorator(csrf_exempt, name="dispatch")
class HomeDashAllView(OAuth2SecuredAPIView):
    """Full dashboard payload."""

    @swagger_auto_schema(
        operation_description="Full dashboard payload for the current user (from the OAuth2 access token).",
        tags=["Home Analytics"],
        manual_parameters=[client_id_param, project_id_param, service_id_param, since_param],
    )
    def get(self, request):
        user, err = self._get_user(request)
        if err:
            return err
        try:
            project_id = request.query_params.get("project_id")
            service_id = request.query_params.get("service_id")
            since = request.query_params.get("since")

            payload = build_overview(
                user=user,
                project_id=project_id,
                service_id=service_id,
                since=since,
            )
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("HomeDashAllView failed")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name="dispatch")
class HomeDashSectionView(OAuth2SecuredAPIView):
    """Single section payload."""

    @swagger_auto_schema(
        operation_description="Return a specific section (user, files, runs, storage, search, ocr, translation, operations, billing, integrations, security, topics, queries, endpoints, insights, highlights).",
        tags=["Home Analytics"],
        manual_parameters=[client_id_param, project_id_param, service_id_param, since_param],
    )
    def get(self, request, section: str):
        user, err = self._get_user(request)
        if err:
            return err
        try:
            fn = SECTIONS.get(section)
            if not fn:
                return Response({"error": f"Unknown section '{section}'"}, status=status.HTTP_404_NOT_FOUND)

            project_id = request.query_params.get("project_id")
            service_id = request.query_params.get("service_id")
            since = request.query_params.get("since")

            data = fn(user=user, project_id=project_id, service_id=service_id, since=since)
            return Response({"section": section, "data": data}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("HomeDashSectionView failed")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name="dispatch")
class HomeDashSnapshotView(OAuth2SecuredAPIView):
    """Latest stored snapshot."""

    @swagger_auto_schema(
        operation_description="Most recent stored snapshot of analytics for the current user.",
        tags=["Home Analytics"],
        manual_parameters=[client_id_param],
    )
    def get(self, request):
        user, err = self._get_user(request)
        if err:
            return err
        try:
            s = (
                HomeAnalyticsSnapshot.objects
                .filter(user=user)
                .order_by("-generated_at")
                .first()
            )
            if not s:
                return Response({"detail": "No snapshot available"}, status=status.HTTP_404_NOT_FOUND)

            return Response(
                {
                    "generated_at": s.generated_at,
                    "generated_async": s.generated_async,
                    "task_id": s.task_id,
                    "window_since": s.window_since,
                    "payload": s.payload,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("HomeDashSnapshotView failed")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Optional extras
@method_decorator(csrf_exempt, name="dispatch")
class HomeDashCardsView(OAuth2SecuredAPIView):
    @swagger_auto_schema(
        tags=["Home Analytics"],
        manual_parameters=[client_id_param, project_id_param, service_id_param],
    )
    def get(self, request):
        user, err = self._get_user(request)
        if err:
            return err
        try:
            project_id = request.query_params.get("project_id")
            service_id = request.query_params.get("service_id")
            return Response(
                build_cards(user=user, project_id=project_id, service_id=service_id),
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("HomeDashCardsView failed")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name="dispatch")
class HomeDashTimeSeriesView(OAuth2SecuredAPIView):
    @swagger_auto_schema(
        tags=["Home Analytics"],
        manual_parameters=[client_id_param, range_param, from_param, to_param],
    )
    def get(self, request):
        user, err = self._get_user(request)
        if err:
            return err
        try:
            return Response(
                build_timeseries(
                    user=user,
                    range=request.query_params.get("range"),
                    date_from=request.query_params.get("from"),
                    date_to=request.query_params.get("to"),
                ),
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("HomeDashTimeSeriesView failed")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name="dispatch")
class HomeDashTopFilesView(OAuth2SecuredAPIView):
    @swagger_auto_schema(
        tags=["Home Analytics"],
        manual_parameters=[client_id_param, openapi.Parameter("limit", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False)],
    )
    def get(self, request):
        user, err = self._get_user(request)
        if err:
            return err
        try:
            limit = int(request.query_params.get("limit", "10"))
            return Response(build_top_files(user, limit), status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("HomeDashTopFilesView failed")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name="dispatch")
class HomeDashTopSearchesView(OAuth2SecuredAPIView):
    @swagger_auto_schema(
        tags=["Home Analytics"],
        manual_parameters=[client_id_param, openapi.Parameter("limit", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False)],
    )
    def get(self, request):
        user, err = self._get_user(request)
        if err:
            return err
        try:
            limit = int(request.query_params.get("limit", "10"))
            return Response(build_top_searches(user, limit), status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("HomeDashTopSearchesView failed")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

