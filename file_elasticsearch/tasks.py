# file_elasticsearch/tasks.py

from celery import shared_task
from .utils import force_reindex

@shared_task
def reindex_files_task():
    force_reindex()
    return "Reindex completed"

