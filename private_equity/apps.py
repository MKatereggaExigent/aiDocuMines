from django.apps import AppConfig


class PrivateEquityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'private_equity'
    verbose_name = 'Private Equity Due Diligence'
    
    def ready(self):
        """
        Called when Django loads the app.
        Import signal handlers if needed.
        """
        # Import signals if you create any
        # import private_equity.signals
        pass
