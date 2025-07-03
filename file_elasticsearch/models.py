# file_elasticsearch/models.py

from django.db import models

class DummyModel(models.Model):
    """
    Just a placeholder if we ever need Django signals.
    """
    name = models.CharField(max_length=255)

