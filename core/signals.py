from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from core.models import File
from core.elastic_indexes import FileIndex

@receiver(post_save, sender=File)
def index_file(sender, instance, **kwargs):
    """
    Called whenever a File is created or updated.
    Saves the File into the Elasticsearch index.
    """
    doc = FileIndex(
        meta={'id': str(instance.id)},
        id=str(instance.id),
        filename=instance.filename,
        filepath=instance.filepath,
        file_size=instance.file_size,
        status=instance.status,
        project_id=instance.project_id,
        service_id=instance.service_id,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
        md5_hash=instance.md5_hash,
        user_id=instance.user.id if instance.user else None,
    )
    doc.save()
    print(f"Indexed file {instance.id} -> Elasticsearch.")

@receiver(post_delete, sender=File)
def delete_file_from_index(sender, instance, **kwargs):
    """
    Called whenever a File is deleted.
    Deletes the File from the Elasticsearch index.
    """
    try:
        doc = FileIndex.get(id=str(instance.id))
        doc.delete()
        print(f"Deleted file {instance.id} from Elasticsearch index.")
    except FileIndex.DoesNotExist:
        print(f"File {instance.id} not found in Elasticsearch index; skipping delete.")

