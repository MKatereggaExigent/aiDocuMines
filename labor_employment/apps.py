from django.apps import AppConfig


class LaborEmploymentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'labor_employment'
    verbose_name = 'Labor and Employment Law'
    
    def ready(self):
        """
        Called when Django loads the app.
        Import signal handlers if needed.
        """
        # Import signals if you create any
        # import labor_employment.signals
        pass
