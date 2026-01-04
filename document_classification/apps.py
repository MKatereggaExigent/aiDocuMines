"""
Document Classification App Configuration
"""

from django.apps import AppConfig


class DocumentClassificationConfig(AppConfig):
    """Django app configuration for document classification."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'document_classification'
    verbose_name = 'Document Classification'
    
    def ready(self):
        """
        Called when the app is ready.
        Import signals or perform other initialization here.
        """
        pass

