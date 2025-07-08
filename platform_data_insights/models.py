# platform_data_insights/models.py

from django.db import models
from django.contrib.auth import get_user_model
import uuid
from django.utils import timezone

User = get_user_model()

class UserInsights(models.Model):
    """
    Stores the aggregated insights for a user, as a JSON snapshot.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="insights",
        db_index=True
    )

    insights_data = models.JSONField(null=True, blank=True)

    # Timestamp info
    generated_at = models.DateTimeField(default=timezone.now)

    # Optional: track how it was generated
    generated_async = models.BooleanField(default=False)
    task_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Insights for {self.user.username} at {self.generated_at}"

