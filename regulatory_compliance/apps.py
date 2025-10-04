from django.apps import AppConfig


class RegulatoryComplianceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'regulatory_compliance'
    verbose_name = 'Regulatory Compliance'
    
    def ready(self):
        """
        Called when Django loads the app.
        Import signal handlers if needed.
        """
        # Import signals if you create any
        # import regulatory_compliance.signals
        pass
