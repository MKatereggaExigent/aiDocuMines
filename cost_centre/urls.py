from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CatalogView,
    EventLogViewSet,
    TokenUsageViewSet,
    BudgetViewSet,
    SubscriptionViewSet,
    UsageSummaryView,
    PreflightCheckView,
    FinalizeUsageView,
    TenantUsageAdminView,
    PaymentHistoryViewSet,
    StripeWebhookView,
    WhoAmIView
)

router = DefaultRouter()
router.register(r"events", EventLogViewSet, basename="cost-events")
router.register(r"tokens", TokenUsageViewSet, basename="cost-tokens")
router.register(r"budgets", BudgetViewSet, basename="cost-budgets")
router.register(r"subscriptions", SubscriptionViewSet, basename="cost-subscriptions")
router.register(r"payments", PaymentHistoryViewSet, basename="cost-payments")

urlpatterns = [
    path("catalog/", CatalogView.as_view(), name="cost-catalog"),
    path("summary/", UsageSummaryView.as_view(), name="cost-summary"),
    path("preflight/", PreflightCheckView.as_view(), name="cost-preflight"),
    path("finalize/", FinalizeUsageView.as_view(), name="cost-finalize"),
    path("admin/tenant/summary", TenantUsageAdminView.as_view(), name="cost-admin-tenant-summary"),
    path("stripe/webhook/", StripeWebhookView.as_view(), name="cost-stripe-webhook"),
    path("whoami/", WhoAmIView.as_view(), name="cost-whoami"),
    path("", include(router.urls)),
]

