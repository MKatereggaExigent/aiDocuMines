# cost_centre/tasks.py
from __future__ import annotations

import math
import time
import logging
from typing import Any, Dict, Optional

from celery import shared_task, Task
from celery.exceptions import SoftTimeLimitExceeded
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.conf import settings

from .models import (
    EventLog,
    TokenUsage,
    Budget,
    Subscription,
)
from . import utils

logger = logging.getLogger(__name__)
User = get_user_model()

# =====================================================================
# Base Task with sane defaults
# =====================================================================
class BaseCostCentreTask(Task):
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 5, "countdown": 5}
    retry_backoff = True           # exponential backoff
    retry_backoff_max = 300        # 5 minutes max backoff
    retry_jitter = True
    acks_late = True               # task won't be acked until finished
    time_limit = 60 * 15           # hard 15 min
    soft_time_limit = 60 * 10      # soft 10 min (allow graceful handling)
    ignore_result = False

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"[{self.name}] FAILED id={task_id} exc={exc} args={args} kwargs={kwargs}")

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"[{self.name}] OK id={task_id}")

# =====================================================================
# Helpers
# =====================================================================
def _get_user(user_id: int) -> User:
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise ValueError(f"User {user_id} not found")

def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default

def _estimate_tokens_from_text(text: str) -> int:
    """
    Naive token estimate. Replace with your tokenizer if needed.
    ~4 chars per token is a rough heuristic for English.
    """
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))

def _notify_limit_alert(user: User, kind: str, used: int, limit: int, threshold_pct: int) -> None:
    """
    Minimal notifier stub. Wire this to your email/Slack system if desired.
    """
    subject = f"[CostCentre] {kind.capitalize()} limit alert"
    message = (
        f"User {getattr(user, 'email', user.id)} has used {used} of {limit} "
        f"({threshold_pct}% threshold reached)."
    )
    logger.warning(f"{subject}: {message}")
    # TODO: integrate with your real notification system (email/Slack/etc.)

# =====================================================================
# PRE-FLIGHT: enforce entitlements/limits before starting heavy work
# =====================================================================
@shared_task(bind=True, base=BaseCostCentreTask, name="cost_centre.preflight_check")
def preflight_check_task(self, *, user_id: int, service_code: str,
                         est_tokens: int = 0, est_pages: int = 0) -> Dict[str, Any]:
    user = _get_user(user_id)
    try:
        utils.enforce_preflight_limits(user, service_code, est_tokens, est_pages)
        return {
            "ok": True,
            "message": "Preflight check passed",
            "service_code": service_code,
            "est_tokens": est_tokens,
            "est_pages": est_pages,
        }
    except Exception as e:
        logger.warning(f"Preflight denied for user={user_id} service={service_code}: {e}")
        return {
            "ok": False,
            "message": str(e),
            "service_code": service_code,
            "est_tokens": est_tokens,
            "est_pages": est_pages,
        }

# =====================================================================
# CORE: record event + usage (idempotent)
# =====================================================================
@shared_task(bind=True, base=BaseCostCentreTask, name="cost_centre.record_event_and_usage")
def record_event_and_usage_task(self, *, user_id: int, service_code: str,
                                tokens_used: int, metadata: Optional[Dict[str, Any]] = None,
                                idempotency_key: Optional[str] = None) -> Dict[str, Any]:
    user = _get_user(user_id)
    with transaction.atomic():
        event, tusage = utils.record_event_and_usage(
            user=user,
            service_code=service_code,
            tokens_used=_safe_int(tokens_used),
            metadata=metadata or {},
            idempotency_key=idempotency_key,
        )
    return {
        "event_id": event.id,
        "token_usage_id": getattr(tusage, "id", None),
    }

# =====================================================================
# CORE: finalize & bill — preferred single call after work completes
# =====================================================================
@shared_task(bind=True, base=BaseCostCentreTask, name="cost_centre.finalize_and_bill")
def finalize_and_bill_task(self, *, user_id: int, service_code: str,
                           actual_tokens_used: int,
                           actual_pages_processed: int = 0,
                           metadata: Optional[Dict[str, Any]] = None,
                           idempotency_key: Optional[str] = None) -> Dict[str, Any]:
    user = _get_user(user_id)
    try:
        summary = utils.finalize_and_bill(
            user=user,
            service_code=service_code,
            actual_tokens_used=_safe_int(actual_tokens_used),
            actual_pages_processed=_safe_int(actual_pages_processed),
            metadata=metadata or {},
            idempotency_key=idempotency_key,
        )
        return {"ok": True, "summary": summary}
    except SoftTimeLimitExceeded:
        logger.error(f"finalize_and_bill soft time limit exceeded: user={user_id}")
        raise
    except Exception as e:
        logger.error(f"finalize_and_bill failed: user={user_id} service={service_code} err={e}")
        raise

# =====================================================================
# EXAMPLE “WORK” TASKS — integrate your real pipelines here
# =====================================================================
@shared_task(bind=True, base=BaseCostCentreTask, name="cost_centre.process_translation")
def process_translation_task(self, *, user_id: int, document_id: int,
                             text: str, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Paid service pipeline example:
      1) estimate tokens -> preflight
      2) do work
      3) finalize & bill with *actual* tokens
    Replace the middle section with your real translation flow.
    """
    user = _get_user(user_id)
    service_code = "translation"
    est_tokens = _estimate_tokens_from_text(text)

    # 1) Preflight
    utils.enforce_preflight_limits(user, service_code, est_tokens, 0)

    # 2) Do your translation work (placeholder)
    time.sleep(0.1)

    # Real systems should capture actual provider tokens used:
    actual_tokens = est_tokens

    # 3) Finalize & bill
    summary = utils.finalize_and_bill(
        user=user,
        service_code=service_code,
        actual_tokens_used=actual_tokens,
        actual_pages_processed=0,
        metadata={"document_id": document_id},
        idempotency_key=idempotency_key,
    )

    return {
        "ok": True,
        "document_id": document_id,
        "tokens_used": actual_tokens,
        "cost_centre": summary,
    }

@shared_task(bind=True, base=BaseCostCentreTask, name="cost_centre.process_redaction")
def process_redaction_task(self, *, user_id: int, document_id: int,
                           redaction_spec: Dict[str, Any],
                           est_pages: int = 1,
                           idempotency_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Paid service example that is page-bound (OCR/redaction).
    Adjust logic if you also measure tokens.
    """
    user = _get_user(user_id)
    service_code = "redact"

    # 1) Preflight
    utils.enforce_preflight_limits(user, service_code, 0, est_pages)

    # 2) Do your redaction work (placeholder)
    time.sleep(0.1)

    actual_tokens = 0
    actual_pages = est_pages  # swap for precise page count if you have it

    # 3) Finalize & bill
    summary = utils.finalize_and_bill(
        user=user,
        service_code=service_code,
        actual_tokens_used=actual_tokens,
        actual_pages_processed=actual_pages,
        metadata={"document_id": document_id, "spec": redaction_spec},
        idempotency_key=idempotency_key,
    )

    return {
        "ok": True,
        "document_id": document_id,
        "pages_processed": actual_pages,
        "tokens_used": actual_tokens,
        "cost_centre": summary,
    }

# =====================================================================
# STRIPE SYNC TASKS
# =====================================================================
@shared_task(bind=True, base=BaseCostCentreTask, name="cost_centre.stripe_sync_subscription_status")
def stripe_sync_subscription_status_task(self, *, subscription_id: int) -> Dict[str, Any]:
    """
    Sync a single subscription’s status from Stripe (useful after webhook or periodically).
    Assumes Subscription has `stripe_subscription_id`.
    """
    sub = Subscription.objects.filter(id=subscription_id).first()
    if not sub or not sub.stripe_subscription_id:
        return {"ok": False, "message": "Subscription not found or missing stripe id"}
    try:
        import stripe
        stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", None)
        stripe_sub = stripe.Subscription.retrieve(sub.stripe_subscription_id)
        sub.stripe_status = stripe_sub.get("status", sub.stripe_status)
        sub.save(update_fields=["stripe_status", "updated_at"])
        return {"ok": True, "status": sub.stripe_status}
    except Exception as e:
        logger.error(f"Stripe sync failed for subscription {subscription_id}: {e}")
        raise

@shared_task(bind=True, base=BaseCostCentreTask, name="cost_centre.stripe_backfill_usage")
def stripe_backfill_usage_task(self, *, subscription_id: int,
                               tokens_delta: int = 0, pages_delta: int = 0) -> Dict[str, Any]:
    """
    If you need to push late usage (e.g., after a short outage),
    you can call this to increment Stripe metered items.
    """
    sub = Subscription.objects.filter(id=subscription_id).first()
    if not sub:
        return {"ok": False, "message": "Subscription not found"}

    pushed = {"tokens": 0, "pages": 0}
    try:
        if tokens_delta > 0 and getattr(sub, "tokens_item_id", None):
            utils.stripe_report_metered_usage(sub, "tokens_item_id", int(tokens_delta))
            pushed["tokens"] = int(tokens_delta)
        if pages_delta > 0 and getattr(sub, "pages_item_id", None):
            utils.stripe_report_metered_usage(sub, "pages_item_id", int(pages_delta))
            pushed["pages"] = int(pages_delta)
        return {"ok": True, "pushed": pushed}
    except Exception as e:
        logger.error(f"Backfill usage failed for sub={subscription_id}: {e}")
        raise

# =====================================================================
# PERIODIC / CRON TASKS
# =====================================================================
@shared_task(bind=True, base=BaseCostCentreTask, name="cost_centre.send_limit_alerts")
def send_limit_alerts_task(self) -> Dict[str, Any]:
    """
    Scan all budgets and send alert when approaching or exceeding limits.
    Run daily/hourly via Celery Beat.
    """
    now = timezone.now()
    start, end = utils.current_billing_window(now)
    alerts_sent = 0

    qs = Budget.objects.select_related("user", "tenant")
    for b in qs.iterator():
        user = b.user
        tenant = utils.get_tenant_for_user(user)

        used_tokens = (
            TokenUsage.objects
            .filter(user=user, tenant=tenant, created_at__gte=start, created_at__lt=end)
            .aggregate(s=Sum("tokens_used"))["s"] or 0
        )

        # Alert at 90% token usage
        if b.token_limit and used_tokens >= int(0.9 * b.token_limit):
            try:
                _notify_limit_alert(user, "token", used_tokens, b.token_limit, 90)
                alerts_sent += 1
            except Exception as e:
                logger.warning(f"Notify token limit failed for user={user.id}: {e}")

        # Add financial limit checks here if you maintain spend snapshots.

    return {"ok": True, "alerts_sent": alerts_sent}

@shared_task(bind=True, base=BaseCostCentreTask, name="cost_centre.rollup_storage_and_pages")
def rollup_storage_and_pages_task(self) -> Dict[str, Any]:
    """
    Periodic task to “snapshot” storage/pages usage at tenant level.
    If you keep these metrics elsewhere, you can copy them into a reporting table.
    Here we just trigger the aggregators so caches/warmers can run.
    """
    logger.info("rollup_storage_and_pages_task executed (implement persistence if needed).")
    return {"ok": True}

# =====================================================================
# QUICK GUARDS FOR TASK-ONLY FLOWS
# =====================================================================
@shared_task(bind=True, base=BaseCostCentreTask, name="cost_centre.preflight_then_finalize")
def preflight_then_finalize_task(self, *, user_id: int, service_code: str,
                                 est_tokens: int = 0, est_pages: int = 0,
                                 actual_tokens_used: int = 0, actual_pages_processed: int = 0,
                                 metadata: Optional[Dict[str, Any]] = None,
                                 idempotency_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience task for simple flows that don’t need a separate “work” task:
      - preflight check
      - immediate finalize & bill with provided actuals
    """
    user = _get_user(user_id)

    # Preflight
    utils.enforce_preflight_limits(user, service_code, est_tokens, est_pages)

    # Finalize
    summary = utils.finalize_and_bill(
        user=user,
        service_code=service_code,
        actual_tokens_used=_safe_int(actual_tokens_used),
        actual_pages_processed=_safe_int(actual_pages_processed),
        metadata=metadata or {},
        idempotency_key=idempotency_key,
    )

    return {
        "ok": True,
        "summary": summary,
    }

