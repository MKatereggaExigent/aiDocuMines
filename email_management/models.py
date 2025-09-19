from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class EmailType(models.TextChoices):
    SUPPORT_TICKET_OPENED = "support_ticket_opened", "Support: Ticket Opened"
    SUPPORT_TICKET_UPDATED = "support_ticket_updated", "Support: Ticket Updated"
    SUPPORT_TICKET_CLOSED  = "support_ticket_closed",  "Support: Ticket Closed"
    INFO_ANNOUNCEMENT      = "info_announcement",      "Information / Announcement"
    BUG_REPORT             = "bug_report",             "Bug Report"
    BUG_FIX_RELEASED       = "bug_fix_released",       "Bug Fix Released"
    FEATURE_REQUEST        = "feature_request",        "Feature Request"
    FEATURE_SHIPPED        = "feature_shipped",        "Feature Shipped"
    SIGNUP_WELCOME         = "signup_welcome",         "Signup: Welcome"
    SIGNUP_VERIFICATION    = "signup_verification",    "Signup: Verification"
    PASSWORD_RESET         = "password_reset",         "Password Reset"
    BILLING_INVOICE        = "billing_invoice",        "Billing: Invoice"
    BILLING_OVERAGE        = "billing_overage",        "Billing: Overage"
    BILLING_PAYMENT_FAILED = "billing_payment_failed", "Billing: Payment Failed"
    SECURITY_ALERT         = "security_alert",         "Security Alert"
    WEEKLY_DIGEST          = "weekly_digest",          "Weekly Digest"
    CUSTOM                 = "custom",                 "Custom"


class EmailTemplate(models.Model):
    """
    Store renderable templates (Django template syntax).
    """
    code = models.SlugField(unique=True, max_length=80, help_text="Stable key, e.g. 'welcome'.")
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)

    subject_template = models.TextField(help_text="Django template for subject")
    body_text_template = models.TextField(blank=True, help_text="Plain-text template")
    body_html_template = models.TextField(blank=True, help_text="HTML template")

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class EmailAttachment(models.Model):
    """
    Attachment can be an uploaded file or reference to an internal core.File.
    """
    uploaded = models.FileField(upload_to="email_attachments/", blank=True, null=True)
    filename = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    size = models.BigIntegerField(default=0)

    core_file = models.ForeignKey(
        "core.File", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        if self.filename:
            return self.filename
        if self.uploaded:
            return self.uploaded.name
        return f"Attachment#{self.pk}"


class OutboxEmail(models.Model):
    """
    Queue of emails to send via Celery.
    """
    STATUS_PENDING = "pending"
    STATUS_SENDING = "sending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SENDING, "Sending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    # Tenancy / ownership hints
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="outbox_emails")
    client_id = models.CharField(max_length=64, blank=True)

    template = models.ForeignKey(EmailTemplate, null=True, blank=True, on_delete=models.SET_NULL, related_name="uses")
    context = models.JSONField(default=dict, blank=True)

    # NEW: classify the email (matches serializers/views)
    email_type = models.CharField(
        max_length=64,
        choices=EmailType.choices,
        default=EmailType.CUSTOM,
        db_index=True,
    )

    from_email = models.EmailField(blank=True)
    reply_to = models.JSONField(default=list, blank=True)   # list[str]
    headers = models.JSONField(default=dict, blank=True)    # dict[str, str]

    to = models.JSONField(default=list, blank=True)         # list[str]
    cc = models.JSONField(default=list, blank=True)
    bcc = models.JSONField(default=list, blank=True)

    # Rendered snapshot
    subject = models.CharField(max_length=255, blank=True)
    body_text = models.TextField(blank=True)
    body_html = models.TextField(blank=True)

    attachments = models.ManyToManyField(EmailAttachment, blank=True)

    scheduled_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    priority = models.PositiveSmallIntegerField(default=50, help_text="Lower = sooner")

    attempt_count = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    message_id = models.CharField(max_length=190, blank=True)
    provider_id = models.CharField(max_length=190, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "scheduled_at", "priority"]),
            models.Index(fields=["client_id"]),
            models.Index(fields=["user"]),
            models.Index(fields=["email_type"]),
        ]
        ordering = ["priority", "scheduled_at", "id"]

    def __str__(self) -> str:
        to = ", ".join(self.to or [])
        subj = self.subject or "(no subject)"
        return f"[{self.status}] {subj} → {to}"


class EmailMessageLog(models.Model):
    """
    Append-only lifecycle log for OutboxEmail.
    """
    EVENT_CHOICES = [
        ("queued", "Queued"),
        ("rendered", "Rendered"),
        ("sending", "Sending"),
        ("sent", "Sent"),
        ("failure", "Failure"),
        ("cancelled", "Cancelled"),
        ("opened", "Opened"),
        ("bounced", "Bounced"),
        ("complained", "Complained"),
    ]

    outbox = models.ForeignKey(OutboxEmail, on_delete=models.CASCADE, related_name="logs")
    event = models.CharField(max_length=32, choices=EVENT_CHOICES)
    details = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-at"]

    def __str__(self) -> str:
        return f"{self.outbox_id} {self.event} @ {self.at:%Y-%m-%d %H:%M:%S}"

