from django.apps import AppConfig

class DocumentAnonymizerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "document_anonymizer"

    def ready(self):
        """Ensure Celery registers the tasks when Django starts."""
        import document_anonymizer.tasks  # Ensure tasks are imported
