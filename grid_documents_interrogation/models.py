from django.db import models
from django.conf import settings
from core.models import File

User = settings.AUTH_USER_MODEL

class Topic(models.Model):
    """
    Represents a logical grouping based on a project and service identifier.
    Replaces the old 'Topic' concept with `project_id` and `service_id`.
    """
    name = models.CharField(max_length=100)
    project_id = models.CharField(max_length=255, db_index=True)
    service_id = models.CharField(max_length=255, db_index=True)
    user = models.ForeignKey(User, related_name='topics', on_delete=models.CASCADE)
    chat_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - Project: {self.project_id}, Service: {self.service_id}"

class Query(models.Model):
    """
    Represents a query-response pair under a topic.
    """
    topic = models.ForeignKey(Topic, related_name='queries', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    file = models.ForeignKey(File, related_name='queries', on_delete=models.SET_NULL, null=True, blank=True)
    query_text = models.TextField()
    response_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Query by {self.user.email if self.user else 'Unknown'} - {self.query_text[:30]}"

