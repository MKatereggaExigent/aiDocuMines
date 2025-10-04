from django.apps import AppConfig


class IpLitigationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ip_litigation'
    verbose_name = 'Intellectual Property Litigation'
    
    def ready(self):
        """
        Called when Django loads the app.
        Import signal handlers if needed.
        """
        # Import signals if you create any
        # import ip_litigation.signals
        pass
