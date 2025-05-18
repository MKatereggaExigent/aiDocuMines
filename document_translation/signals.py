from django.db.models.signals import post_migrate
from django.dispatch import receiver
from document_translation.utils import load_translation_languages
import logging

logger = logging.getLogger(__name__)

@receiver(post_migrate)
def run_after_migration(sender, **kwargs):
    try:
        load_translation_languages()
    except Exception as e:
        logger.error(f"Failed to load translation languages post-migrate: {e}")

