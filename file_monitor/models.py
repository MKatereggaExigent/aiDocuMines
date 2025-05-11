from core.models import File
from django.db import models
from django.contrib.auth import get_user_model
import uuid
from django.contrib.postgres.fields import ArrayField

User = get_user_model()

class FileEventLog(models.Model):
    file = models.ForeignKey(File, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=50, choices=[("opened", "Opened"), ("modified", "Modified"), ("created", "Created"), ("deleted", "Deleted")])
    path = models.CharField(max_length=1024)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)  # e.g. "Translated to French"
    triggered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    details = models.JSONField(blank=True, null=True)  # Optional extra info

