# integrations/models.py

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class IntegrationLog(models.Model):
    STATUS_CHOICES = [
        ("created", "User Created"),
        ("reset", "Password Reset"),
        ("failed", "Failed"),
        ("error", "Error"),
        ("processing", "Processing"),
        ("skipped", "Skipped"),
        ("success", "Success"),
    ]

    CONNECTOR_CHOICES = [
        ("nextcloud", "Nextcloud"),
        # Add more like ("mattermost", "Mattermost") etc. if needed
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    connector = models.CharField(max_length=50, choices=CONNECTOR_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    autologin_url = models.URLField(blank=True, null=True)  # Optional: store link used

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user} - {self.connector} [{self.status}]"

