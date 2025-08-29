# insights_hub/apps.py
from django.apps import AppConfig
import importlib
from django.conf import settings

class InsightsHubConfig(AppConfig):
    name = "insights_hub"

    def ready(self):
        # Load built-in providers
        importlib.import_module("insights_hub.providers.core_provider")
        importlib.import_module("insights_hub.providers.anonymizer_provider")

        # Optional auto-discovery: load "<app>.insight_providers" if exists
        for app in getattr(settings, "INSTALLED_APPS", []):
            try:
                importlib.import_module(f"{app}.insight_providers")
            except Exception:
                # Silently ignore if module not present
                pass

