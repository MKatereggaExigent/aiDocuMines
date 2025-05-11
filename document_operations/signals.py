# document_operations/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import File
from .models import EffectiveAccess, Folder

DEFAULT_PERMISSIONS = {
    "can_download": True,
    "can_rename": True,
    "can_delete": True,
    "can_move": True,
    "can_share": True,
    "can_zip": True,
    "can_protect": True,
    "can_duplicate": True,
    "can_restore": True
}

@receiver(post_save, sender=File)
def create_effective_access_for_file(sender, instance, created, **kwargs):
    if created:
        EffectiveAccess.objects.get_or_create(
            user=instance.user,
            file=instance,
            defaults=DEFAULT_PERMISSIONS
        )


@receiver(post_save, sender=Folder)
def create_effective_access_for_folder(sender, instance, created, **kwargs):
    if created:
        EffectiveAccess.objects.get_or_create(
            user=instance.user,
            folder=instance,
            defaults=DEFAULT_PERMISSIONS
        )

