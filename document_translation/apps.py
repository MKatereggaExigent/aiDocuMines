from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class DocumentTranslationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "document_translation"

    def ready(self):
        """
        Avoid running database queries at startup.
        The function `load_translation_languages` should only be called
        after the database is ready and migrations are applied.
        """
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'document_translation_translationlanguage'")
                if cursor.fetchone():
                    from document_translation.utils import load_translation_languages
                    load_translation_languages()
                else:
                    logger.warning("Table 'document_translation_translationlanguage' is missing. Skipping language loading.")
        except Exception as e:
            logger.error(f"Database not ready during app initialization: {e}")
