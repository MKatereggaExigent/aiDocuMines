from __future__ import annotations

import traceback

from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import OutboxEmail
from .utils import build_email_message, log, render_into_outbox


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_outbox_email(self, outbox_id: int) -> bool:
    """
    Send a single OutboxEmail by id. Safe for concurrent workers.
    """
    try:
        with transaction.atomic():
            # Lock row to avoid double-send in concurrent workers
            out = (
                OutboxEmail.objects.select_for_update(skip_locked=True)
                .get(pk=outbox_id)
            )

            if out.status not in (OutboxEmail.STATUS_PENDING, OutboxEmail.STATUS_FAILED):
                return True

            # Not yet due?
            if out.scheduled_at and out.scheduled_at > timezone.now():
                return False

            # Attempts exhausted?
            if out.attempt_count >= out.max_attempts:
                out.status = OutboxEmail.STATUS_CANCELLED
                out.last_error = "Max attempts exceeded"
                out.save(update_fields=["status", "last_error"])
                log(out, "cancelled", reason="max_attempts")
                return False

            # Mark as sending
            out.status = OutboxEmail.STATUS_SENDING
            out.attempt_count += 1
            out.last_attempt_at = timezone.now()
            out.save(update_fields=["status", "attempt_count", "last_attempt_at"])

        # Outside the lock: render and send
        render_into_outbox(out)
        msg = build_email_message(out)
        sent = msg.send()  # number of recipients accepted

        out.status = OutboxEmail.STATUS_SENT if sent > 0 else OutboxEmail.STATUS_FAILED
        out.message_id = msg.extra_headers.get("Message-Id", out.message_id)
        out.last_error = "" if sent > 0 else "SMTP backend returned 0 accepted recipients"
        out.save(update_fields=["status", "message_id", "last_error"])

        log(out, "sent" if sent > 0 else "failure", recipients=sent)
        return sent > 0

    except OutboxEmail.DoesNotExist:
        return False

    except Exception as exc:
        try:
            out = OutboxEmail.objects.get(pk=outbox_id)
            out.status = OutboxEmail.STATUS_FAILED
            out.last_error = f"{type(exc).__name__}: {exc}"
            out.save(update_fields=["status", "last_error"])
            log(out, "failure", error=out.last_error, trace=traceback.format_exc()[:4000])
        except Exception:
            pass
        # allow Celery to retry according to policy
        raise


@shared_task
def send_due_outbox_batch(limit: int = 50) -> int:
    """
    Enqueue up to `limit` due emails. Schedule via Celery Beat (e.g., every minute).
    """
    now = timezone.now()
    ids = (
        OutboxEmail.objects
        .filter(status__in=[OutboxEmail.STATUS_PENDING, OutboxEmail.STATUS_FAILED],
                scheduled_at__lte=now)
        .exclude(attempt_count__gte=F("max_attempts"))
        .order_by("priority", "scheduled_at", "id")
        .values_list("id", flat=True)[:limit]
    )
    for pk in ids:
        send_outbox_email.delay(pk)
    return len(ids)

