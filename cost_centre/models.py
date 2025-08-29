from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

# -----------------------------------------------------------------------------------
# Constants / Choices
# -----------------------------------------------------------------------------------

USER_MODEL = settings.AUTH_USER_MODEL  # your CustomUser

class EventType(models.TextChoices):
    FILE_UPLOAD   = "file_upload", "File Upload"
    FILE_EDIT     = "file_edit", "File Edit"
    FILE_DELETE   = "file_delete", "File Delete"
    TRANSLATION   = "translation", "Translation"
    COMMENT       = "comment", "Comment"
    APPROVE       = "approve", "Approve"
    ANONYMIZE    = "anonymize", "Anonymize"
    COPY          = "copy", "Copy"
    REDACT        = "redact", "Redact"
    OPEN_DOC      = "open_document", "Open Document"
    WRITE_DOC     = "write_document", "Write Document"
    OTHER         = "other", "Other"

class ServiceType(models.TextChoices):
    PAYABLE     = "payable", "Payable"
    NON_PAYABLE = "non_payable", "Non-Payable"

class PlanCode(models.TextChoices):
    STARTER     = "starter", "Starter"
    PRO         = "pro", "Pro"
    BUSINESS    = "business", "Business"
    ENTERPRISE  = "enterprise", "Enterprise"
    ELITE       = "elite", "Elite"


# -----------------------------------------------------------------------------------
# Base
# -----------------------------------------------------------------------------------

class BaseModel(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# -----------------------------------------------------------------------------------
# Core models
# -----------------------------------------------------------------------------------

class EventLog(BaseModel):
    """
    Every user-facing action. Acts as the audit spine and source for usage accounting.
    Idempotency prevents duplicate billing/logs on retries.
    """
    user = models.ForeignKey(USER_MODEL, on_delete=models.CASCADE, related_name="cc_events")
    # Your real tenant lives in custom_authentication.Client
    tenant = models.ForeignKey("custom_authentication.Client", on_delete=models.CASCADE, related_name="cc_event_logs")

    event_type = models.CharField(max_length=50, choices=EventType.choices, db_index=True)
    service_type = models.CharField(max_length=20, choices=ServiceType.choices, default=ServiceType.NON_PAYABLE)

    # Optional: keep a plain string idempotency key for fast lookups (faster than JSON queries)
    idempotency_key = models.CharField(max_length=80, blank=True, null=True, db_index=True)

    # Free-form context (file ids, endpoint path, ip, ua, request id, etc.)
    metadata = models.JSONField(default=dict, blank=True)

    # Convenience mirror; actual token rows live in TokenUsage
    tokens_used = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["user", "tenant", "-created_at"], name="cc_evt_user_ten_ts"),
            models.Index(fields=["event_type", "-created_at"], name="cc_evt_type_ts"),
        ]
        constraints = [
            # prevent impossible combinations at DB level when we mirror tokens_used on the event
            models.CheckConstraint(
                check=Q(service_type=ServiceType.PAYABLE) | Q(tokens_used=0),
                name="cc_evt_tokens_zero_if_non_payable",
            ),
            # best-effort idempotency guard (not globally unique to allow null/blank)
            models.UniqueConstraint(
                fields=["user", "tenant", "idempotency_key"],
                name="cc_evt_user_tenant_idem_unique",
                condition=Q(idempotency_key__isnull=False),
            ),
        ]

    def __str__(self):
        return f"{self.event_type} by {getattr(self.user, 'email', self.user_id)} @ {self.created_at:%Y-%m-%d %H:%M:%S}"


class TokenUsage(BaseModel):
    """
    Atomic token usage rows tied to events. Totals are computed per billing cycle.
    """
    user = models.ForeignKey(USER_MODEL, on_delete=models.CASCADE, related_name="cc_token_usage")
    tenant = models.ForeignKey("custom_authentication.Client", on_delete=models.CASCADE, related_name="cc_token_usage")

    tokens_used = models.PositiveIntegerField()
    event_log = models.ForeignKey(EventLog, on_delete=models.SET_NULL, null=True, blank=True, related_name="token_usages")

    class Meta:
        indexes = [
            models.Index(fields=["user", "tenant", "-created_at"], name="cc_tok_user_ten_ts"),
        ]

    def __str__(self):
        return f"{self.tokens_used} tokens by {getattr(self.user, 'email', self.user_id)} @ {self.created_at:%Y-%m-%d}"


class Budget(BaseModel):
    """
    Per-user per-tenant limits for tokens and money (per billing cycle semantics are enforced in code).
    """
    user = models.ForeignKey(USER_MODEL, on_delete=models.CASCADE, related_name="cc_budgets")
    tenant = models.ForeignKey("custom_authentication.Client", on_delete=models.CASCADE, related_name="cc_budgets")

    token_limit = models.PositiveBigIntegerField(default=0)                  # e.g., 1_000_000
    financial_limit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "tenant"], name="cc_budget_user_tenant_unique"),
            models.CheckConstraint(check=Q(token_limit__gte=0), name="cc_budget_token_nonneg"),
            models.CheckConstraint(check=Q(financial_limit__gte=0), name="cc_budget_fin_nonneg"),
        ]
        indexes = [
            models.Index(fields=["tenant", "user"], name="cc_budget_ten_user"),
        ]

    def __str__(self):
        return f"Budget[{self.tenant_id}] for {getattr(self.user, 'email', self.user_id)}"


class Subscription(BaseModel):
    """
    A user's subscription in a tenant (many orgs keep this per-tenant admin user, but per-user also works).
    Adds plan details + Stripe linkage + metered item ids for usage pushes.
    """
    user = models.ForeignKey(USER_MODEL, on_delete=models.CASCADE, related_name="cc_subscriptions")
    tenant = models.ForeignKey("custom_authentication.Client", on_delete=models.CASCADE, related_name="cc_subscriptions")

    # Stripe linkage
    stripe_subscription_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    stripe_payment_method_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_status = models.CharField(max_length=50, default="inactive", db_index=True)

    # Plan / pricing state (aligns to frontend)
    plan_code = models.CharField(max_length=20, choices=PlanCode.choices, default=PlanCode.STARTER)
    seat_count = models.PositiveIntegerField(default=1)
    annual_prepay = models.BooleanField(default=False)

    # Optional: last billed amount at cycle close (for convenience/BI)
    amount_billed = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    # Cycle tracking (used by summaries; utils computes canonical monthly windows)
    billing_cycle_start = models.DateTimeField(default=timezone.now)
    billing_cycle_end = models.DateTimeField(default=timezone.now)

    # Metered items (so we can push usage to Stripe UsageRecord)
    tokens_item_id = models.CharField(max_length=255, blank=True, null=True)
    pages_item_id = models.CharField(max_length=255, blank=True, null=True)
    # Optional per-service items if you want separate lines
    translation_item_id = models.CharField(max_length=255, blank=True, null=True)
    redact_item_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "user", "-updated_at"], name="cc_sub_ten_user_updated"),
            models.Index(fields=["plan_code"], name="cc_sub_plan"),
        ]
        constraints = [
            models.CheckConstraint(check=Q(seat_count__gte=1), name="cc_sub_seats_ge_1"),
        ]

    def __str__(self):
        return f"Sub[{self.plan_code}] {getattr(self.user, 'email', self.user_id)} ({self.stripe_status})"

    @property
    def is_active(self) -> bool:
        return self.stripe_status in {"active", "trialing"}


class PaymentHistory(BaseModel):
    """
    Records payments (typically Stripe invoices/charges). Separate from metered usage pushes.
    """
    user = models.ForeignKey(USER_MODEL, on_delete=models.CASCADE, related_name="cc_payments")
    tenant = models.ForeignKey("custom_authentication.Client", on_delete=models.CASCADE, related_name="cc_payments")

    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")

    payment_date = models.DateTimeField(default=timezone.now, db_index=True)
    payment_method = models.CharField(
        max_length=50,
        choices=[("card", "Credit/Debit Card"), ("bank", "Bank Transfer"), ("paypal", "PayPal"), ("other", "Other")],
        default="card",
    )
    stripe_payment_intent = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "-payment_date"], name="cc_pay_ten_date"),
            models.Index(fields=["user", "-payment_date"], name="cc_pay_user_date"),
        ]
        constraints = [
            models.CheckConstraint(check=Q(amount_paid__gte=0), name="cc_pay_amount_nonneg"),
        ]

    def __str__(self):
        return f"Payment {self.amount_paid} {self.currency} by {getattr(self.user, 'email', self.user_id)} @ {self.payment_date:%Y-%m-%d}"

