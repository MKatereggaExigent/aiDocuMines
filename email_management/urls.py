from __future__ import annotations

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import EmailTemplateViewSet, OutboxEmailViewSet

router = DefaultRouter()
router.register(r"templates", EmailTemplateViewSet, basename="email-template")
router.register(r"outbox", OutboxEmailViewSet, basename="outbox-email")

urlpatterns = [
    path("", include(router.urls)),
]

