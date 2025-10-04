from django.apps import AppConfig


class ClassActionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'class_actions'
    verbose_name = 'Class Action and Mass Claims Management'
    
    def ready(self):
        """
        Called when Django loads the app.
        Import signal handlers if needed.
        """
        # Import signals if you create any
        # import class_actions.signals
        pass
