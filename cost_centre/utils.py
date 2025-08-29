# cost_centre/utils.py
from __future__ import annotations

import decimal
import functools
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

import stripe

from .models import (
    EventLog,
    TokenUsage,
    Budget,
    Subscription,
    PaymentHistory,
)
from custom_authentication.models import Client as Tenant  # real tenant model

logger = logging.getLogger(__name__)
stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", None)

# -----------------------------------------------------------------------------
# Tenant resolver (your auth app uses `user.client`)
# -----------------------------------------------------------------------------
def get_tenant_for_user(user):
    tenant = getattr(user, "client", None) or getattr(user, "tenant", None)
    if tenant is None:
        raise ValidationError("User is not associated with any tenant/client.")
    return tenant

# -----------------------------------------------------------------------------
# Plans & entitlements (align to your Angular pricing tables)
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class PlanEntitlement:
    code: str
    name: str
    price_per_user_month: decimal.Decimal  # list price, USD
    pages_included: int                    # e.g. 100 for Starter
    tokens_included: Optional[int]         # None means “—”; -1 means infinity
    storage_gb_included: int
    highlights: str

# From your pricing.component.html
PLAN_CATALOG: Dict[str, PlanEntitlement] = {
    "starter": PlanEntitlement(
        code="starter", name="Starter", price_per_user_month=decimal.Decimal("0"),
        pages_included=100, tokens_included=None, storage_gb_included=1,
        highlights="Upload, OCR, search, export (no AI)"
    ),
    "pro": PlanEntitlement(
        code="pro", name="Pro", price_per_user_month=decimal.Decimal("49"),
        pages_included=5000, tokens_included=250_000, storage_gb_included=10,
        highlights="Includes AI chat, summaries, insights"
    ),
    "business": PlanEntitlement(
        code="business", name="Business", price_per_user_month=decimal.Decimal("119"),
        pages_included=50_000, tokens_included=1_000_000, storage_gb_included=50,
        highlights="Multi-user, RBAC, translation, anonymisation"
    ),
    "enterprise": PlanEntitlement(
        code="enterprise", name="Enterprise", price_per_user_month=decimal.Decimal("259"),
        pages_included=10**9, tokens_included=5_000_000, storage_gb_included=200,
        highlights="Dedicated infra, SSO, audit logs, SLA"
    ),
    "elite": PlanEntitlement(
        code="elite", name="Elite", price_per_user_month=decimal.Decimal("499"),
        pages_included=10**9, tokens_included=-1, storage_gb_included=500,
        highlights="White-glove onboarding, 24/7 SLA"
    ),
}

# -----------------------------------------------------------------------------
# Overage & add-on pricing (USD)
# -----------------------------------------------------------------------------
OVERAGE = {
    "tokens_per_1m": decimal.Decimal("6.00"),         # $6 per additional 1M tokens
    "pages_per_1k": decimal.Decimal("2.00"),          # $2 per extra 1k pages
    "storage_per_gb_month": decimal.Decimal("0.10"),  # $0.10 / GB / month
    "cloud_api_chars_per_1m": decimal.Decimal("15.00"),
    "premium_support_per_month": decimal.Decimal("500.00"),
    "dedicated_env_from": decimal.Decimal("1200.00"),
}

# -----------------------------------------------------------------------------
# Volume & term discounts
# -----------------------------------------------------------------------------
def volume_discount_pct(seat_count: int) -> decimal.Decimal:
    if seat_count >= 200:
        return decimal.Decimal("0.25")
    if seat_count >= 51:
        return decimal.Decimal("0.20")
    if seat_count >= 11:
        return decimal.Decimal("0.10")
    return decimal.Decimal("0.00")

def term_discount_pct(annual_prepay: bool) -> decimal.Decimal:
    return decimal.Decimal("0.15") if annual_prepay else decimal.Decimal("0.00")

# -----------------------------------------------------------------------------
# Billing cycle
# -----------------------------------------------------------------------------
def current_billing_window(now: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    now = now or timezone.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # next month
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end

# -----------------------------------------------------------------------------
# Idempotency
# -----------------------------------------------------------------------------
def make_idempotency_key(prefix: str = "evt") -> str:
    return f"{prefix}_{uuid.uuid4().hex}_{int(time.time()*1000)}"

def _idempotent_fetch_event(user, tenant, idem_key: str) -> Optional[EventLog]:
    # Use the dedicated column (faster + matches UniqueConstraint)
    return (
        EventLog.objects.select_for_update(of=("self",))
        .filter(user=user, tenant=tenant, idempotency_key=idem_key)
        .first()
    )

# -----------------------------------------------------------------------------
# Service registry (payable/non-payable)
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class ServiceDef:
    code: str
    name: str
    payable: bool
    price_per_1k_tokens: decimal.Decimal = decimal.Decimal("0.00")
    currency: str = "USD"
    stripe_item_key: Optional[str] = None  # subscription_item id field name on Subscription

SERVICE_REGISTRY: Dict[str, ServiceDef] = {
    "translation": ServiceDef("translation", "Translation", True, decimal.Decimal("0.00"), "USD", "translation_item_id"),
    "redact":      ServiceDef("redact", "Redaction", True,    decimal.Decimal("0.00"), "USD", "redact_item_id"),
    "open_document":  ServiceDef("open_document", "Open", False),
    "write_document": ServiceDef("write_document","Write",False),
    # add others…
}

def get_service_def(code: str) -> ServiceDef:
    try:
        return SERVICE_REGISTRY[code]
    except KeyError:
        raise ValidationError(f"Unknown service_code '{code}'")

# -----------------------------------------------------------------------------
# Aggregates (per-cycle)
# -----------------------------------------------------------------------------
def aggregate_tokens(user, tenant, start, end) -> int:
    return int(
        TokenUsage.objects.filter(
            user=user, tenant=tenant,
            created_at__gte=start, created_at__lt=end
        ).aggregate(s=Sum("tokens_used"))["s"] or 0
    )

def aggregate_pages(tenant, start, end) -> int:
    """Implement against your page accounting table."""
    return 0

def aggregate_storage_gb(tenant) -> int:
    """Implement against your storage accounting (current GB used)."""
    return 0

# -----------------------------------------------------------------------------
# Plan lookup on Subscription
# -----------------------------------------------------------------------------
def get_plan_for_user(user) -> PlanEntitlement:
    sub = (
        Subscription.objects
        .filter(user=user, stripe_status__in=["active", "trialing"])
        .order_by("-updated_at")
        .first()
    )
    plan_code = getattr(sub, "plan_code", None) or "starter"
    if plan_code not in PLAN_CATALOG:
        plan_code = "starter"
    return PLAN_CATALOG[plan_code]

# -----------------------------------------------------------------------------
# Entitlement enforcement (pre-flight)
# -----------------------------------------------------------------------------
def enforce_preflight_limits(user, service_code: str, est_tokens: int = 0, est_pages: int = 0) -> None:
    tenant = get_tenant_for_user(user)
    plan = get_plan_for_user(user)
    svc  = get_service_def(service_code)  # noqa: F841 (kept for future per-service rules)

    start, end = current_billing_window()
    used_tokens = aggregate_tokens(user, tenant, start, end)
    used_pages  = aggregate_pages(tenant, start, end)
    used_storage_gb = aggregate_storage_gb(tenant)

    # Tokens: Starter has None (no AI). Elite has -1 (infinite).
    if est_tokens and plan.tokens_included is None:
        raise PermissionDenied("Your plan does not include AI tokens.")
    if plan.tokens_included not in (None, -1):
        if used_tokens + est_tokens > plan.tokens_included:
            logger.info("Token usage will exceed included quota; overage will apply.")

    # Pages:
    if used_pages + est_pages > plan.pages_included:
        logger.info("Page processing will exceed included quota; overage will apply.")

    # Storage:
    if used_storage_gb > plan.storage_gb_included:
        logger.info("Storage exceeds included quota; storage overage will apply.")

# -----------------------------------------------------------------------------
# Overage math
# -----------------------------------------------------------------------------
def tokens_overage_cost(plan: PlanEntitlement, used_tokens: int) -> decimal.Decimal:
    if plan.tokens_included in (None, -1):
        return decimal.Decimal("0.00")
    over = max(0, used_tokens - plan.tokens_included)
    if over == 0:
        return decimal.Decimal("0.00")
    units = decimal.Decimal(over) / decimal.Decimal(1_000_000)  # $/1M tokens
    return (units * OVERAGE["tokens_per_1m"]).quantize(decimal.Decimal("0.01"))

def pages_overage_cost(plan: PlanEntitlement, used_pages: int) -> decimal.Decimal:
    over = max(0, used_pages - plan.pages_included)
    if over == 0:
        return decimal.Decimal("0.00")
    units = decimal.Decimal(over) / decimal.Decimal(1_000)  # $/1k pages
    return (units * OVERAGE["pages_per_1k"]).quantize(decimal.Decimal("0.01"))

def storage_overage_cost(plan: PlanEntitlement, used_storage_gb: int) -> decimal.Decimal:
    over = max(0, used_storage_gb - plan.storage_gb_included)
    if over <= 0:
        return decimal.Decimal("0.00")
    return (decimal.Decimal(over) * OVERAGE["storage_per_gb_month"]).quantize(decimal.Decimal("0.01"))

# -----------------------------------------------------------------------------
# Seat pricing with volume & term discounts
# -----------------------------------------------------------------------------
def monthly_seat_price(plan: PlanEntitlement, seat_count: int, annual_prepay: bool) -> decimal.Decimal:
    base = plan.price_per_user_month
    vol = volume_discount_pct(seat_count)
    term = term_discount_pct(annual_prepay)
    price = base * (decimal.Decimal("1.00") - vol) * (decimal.Decimal("1.00") - term)
    return price.quantize(decimal.Decimal("0.01"))

def monthly_subscription_amount(plan_code: str, seat_count: int, annual_prepay: bool) -> decimal.Decimal:
    plan = PLAN_CATALOG[plan_code]
    return monthly_seat_price(plan, seat_count, annual_prepay) * seat_count

# -----------------------------------------------------------------------------
# Core event + usage recording (atomic, idempotent)
# -----------------------------------------------------------------------------
@transaction.atomic
def record_event_and_usage(
    *,
    user,
    service_code: str,
    tokens_used: int,
    metadata: Optional[Dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
):
    tenant = get_tenant_for_user(user)
    metadata = metadata or {}
    idem = idempotency_key or make_idempotency_key(service_code)

    existing = _idempotent_fetch_event(user, tenant, idem)
    if existing:
        tu = TokenUsage.objects.filter(user=user, tenant=tenant, event_log=existing).first()
        return existing, tu

    svc = get_service_def(service_code)
    e = EventLog.objects.create(
        user=user,
        tenant=tenant,
        event_type=service_code,
        service_type="payable" if svc.payable else "non_payable",
        tokens_used=max(tokens_used, 0),
        idempotency_key=idem,                         # <-- set column
        metadata={**metadata, "idempotency_key": idem},  # optional mirror
    )
    tu = None
    if tokens_used > 0:
        tu = TokenUsage.objects.create(
            user=user,
            tenant=tenant,
            tokens_used=max(tokens_used, 0),
            event_log=e,
        )
    return e, tu

# -----------------------------------------------------------------------------
# Stripe helpers
# -----------------------------------------------------------------------------
def get_active_subscription(user) -> Optional[Subscription]:
    tenant = get_tenant_for_user(user)
    return (
        Subscription.objects
        .filter(user=user, tenant=tenant, stripe_status__in=["active", "trialing"])
        .order_by("-updated_at")
        .first()
    )

def stripe_report_metered_usage(subscription: Subscription, item_field: str, quantity: int):
    if not stripe.api_key or quantity <= 0:
        return
    item_id = getattr(subscription, item_field, None)
    if not item_id:
        return
    try:
        stripe.UsageRecord.create(
            subscription_item=item_id,
            quantity=int(quantity),
            timestamp=int(time.time()),
            action="increment",
        )
    except Exception as e:
        logger.error(f"Stripe UsageRecord failed ({item_field}): {e}")

# -----------------------------------------------------------------------------
# Finalize usage & compute overages
# -----------------------------------------------------------------------------
@transaction.atomic
def finalize_and_bill(
    *,
    user,
    service_code: str,
    actual_tokens_used: int,
    actual_pages_processed: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    1) Writes EventLog + TokenUsage (idempotent).
    2) Computes cycle-to-date usage and overages against the plan.
    3) Optionally reports metered usage to Stripe for add-ons.
    Returns a dict suitable for API responses.
    """
    tenant = get_tenant_for_user(user)
    plan = get_plan_for_user(user)
    svc  = get_service_def(service_code)  # noqa: F841

    e, tu = record_event_and_usage(
        user=user,
        service_code=service_code,
        tokens_used=actual_tokens_used,
        metadata=metadata,
        idempotency_key=idempotency_key,
    )

    # cycle aggregates after write
    start, end = current_billing_window()
    used_tokens = aggregate_tokens(user, tenant, start, end)
    used_pages  = aggregate_pages(tenant, start, end)
    used_storage_gb = aggregate_storage_gb(tenant)

    # overage costs snapshot
    token_over = tokens_overage_cost(plan, used_tokens)
    page_over  = pages_overage_cost(plan, used_pages)
    storage_over = storage_overage_cost(plan, used_storage_gb)

    # optional Stripe metered reporting for add-ons (tokens/pages)
    sub = get_active_subscription(user)
    if sub:
        if actual_tokens_used > 0 and getattr(sub, "tokens_item_id", None):
            stripe_report_metered_usage(sub, "tokens_item_id", actual_tokens_used)
        if actual_pages_processed > 0 and getattr(sub, "pages_item_id", None):
            stripe_report_metered_usage(sub, "pages_item_id", actual_pages_processed)

    return {
        "event_id": e.id,
        "tokens_used_cycle": used_tokens,
        "pages_processed_cycle": used_pages,
        "storage_gb_current": used_storage_gb,
        "overage": {
            "tokens_usd": str(token_over),
            "pages_usd": str(page_over),
            "storage_usd": str(storage_over),
            "currency": "USD",
        },
        "plan": {
            "code": plan.code,
            "name": plan.name,
            "included": {
                "tokens": plan.tokens_included,
                "pages": plan.pages_included,
                "storage_gb": plan.storage_gb_included,
            },
        },
    }

# -----------------------------------------------------------------------------
# Decorator to enforce & finalize automatically
# -----------------------------------------------------------------------------
def cost_guard(service_code: str, estimate_tokens=None, estimate_pages=None):
    """
    Wrap DRF view methods or Celery tasks.
    - Pre: enforce based on estimates (soft for overages, hard-stop for no-token plans).
    - Post: finalize_and_bill using returned 'tokens_used' and 'pages_processed' fields.
    """
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            # resolve user & request (DRF)
            request = None
            user = kwargs.get("user")
            if not user and args:
                # View method: (self, request, ...)
                if len(args) > 1 and hasattr(args[1], "user"):
                    request = args[1]
                    user = request.user

            if not user or not getattr(user, "is_authenticated", False):
                raise PermissionDenied("Authentication required.")

            est_toks = 0
            est_pgs  = 0
            if callable(estimate_tokens):
                try:
                    est_toks = int(estimate_tokens(*args, **kwargs)) or 0
                except Exception:
                    est_toks = 0
            if callable(estimate_pages):
                try:
                    est_pgs = int(estimate_pages(*args, **kwargs)) or 0
                except Exception:
                    est_pgs = 0

            enforce_preflight_limits(user, service_code, est_toks, est_pgs)

            idem = make_idempotency_key(service_code)
            kwargs["idempotency_key"] = idem

            result = fn(*args, **kwargs)

            # pull actual usage
            data = getattr(result, "data", None) or result
            actual_tokens = int((data or {}).get("tokens_used", 0) or 0)
            actual_pages  = int((data or {}).get("pages_processed", 0) or 0)

            try:
                summary = finalize_and_bill(
                    user=user,
                    service_code=service_code,
                    actual_tokens_used=actual_tokens,
                    actual_pages_processed=actual_pages,
                    metadata={"endpoint": getattr(request, "path", None)},
                    idempotency_key=idem,
                )
                if hasattr(result, "data"):
                    result.data["cost_centre"] = summary
                elif isinstance(result, dict):
                    result["cost_centre"] = summary
            except Exception as e:
                logger.error(f"finalize_and_bill failed: {e}")

            return result
        return wrapper
    return deco

# -----------------------------------------------------------------------------
# Quote helpers for frontend (seats, discounts)
# -----------------------------------------------------------------------------
def quote_monthly(plan_code: str, seat_count: int, annual_prepay: bool) -> Dict[str, Any]:
    plan = PLAN_CATALOG[plan_code]
    vol = str((volume_discount_pct(seat_count) * 100).quantize(decimal.Decimal("0")))
    term = "15" if annual_prepay else "0"
    amount = monthly_subscription_amount(plan_code, seat_count, annual_prepay)
    return {
        "plan": plan.name,
        "seat_count": seat_count,
        "volume_discount_pct": vol,
        "term_discount_pct": term,
        "total_monthly_usd": str(amount),
        "currency": "USD",
    }

