# tasks.py
from celery import shared_task
from core.models import File
from .models import Folder, FileVersion, FileAuditLog, FileFolderLink
from django.contrib.auth import get_user_model
from .utils import (
    move_files_to_trash,
    reassign_folder_for_files,
    rename_file,
    rename_folder,
    delete_file,
    delete_folder,
    duplicate_file,
    copy_file,
    zip_files,
    protect_file_with_password,
    restore_file_from_trash,
    restore_folder_from_trash,
)
import os

User = get_user_model()

@shared_task
def async_bulk_trash_files(file_ids):
    updated_count = move_files_to_trash(file_ids)
    return {
        "message": f"Moved {updated_count} file(s) to trash.",
        "file_ids": file_ids,
    }

@shared_task
def async_bulk_move_files_to_folder(file_ids, folder_id):
    try:
        folder = Folder.objects.get(id=folder_id)
    except Folder.DoesNotExist:
        return {"error": "Target folder does not exist."}

    links = reassign_folder_for_files(file_ids, folder)
    return {
        "message": f"Moved {len(links)} file(s) to folder '{folder.name}'.",
        "folder_id": folder_id,
        "file_ids": file_ids,
    }

@shared_task
def async_rename_file(file_id, new_name):
    try:
        file = File.objects.get(id=file_id)
    except File.DoesNotExist:
        return {"error": f"File with ID {file_id} does not exist."}

    old_path = file.filepath
    new_path = os.path.join(os.path.dirname(old_path), new_name)

    if os.path.exists(old_path):
        os.rename(old_path, new_path)

    file.filename = new_name
    file.filepath = new_path
    file.save()

    FileAuditLog.objects.create(file=file, user=file.user, action="renamed", notes=f"Renamed to {new_name}")
    return {"message": f"File renamed to {new_name}", "file_id": file.id}

@shared_task
def async_rename_folder(folder_id, new_name):
    folder = Folder.objects.get(id=folder_id)
    rename_folder(folder, new_name)
    return {"message": f"Folder renamed to {new_name}", "folder_id": folder_id}

@shared_task
def async_delete_file(file_link_id):
    link = FileFolderLink.objects.get(id=file_link_id)
    FileAuditLog.objects.create(file=link.file, user=link.file.user, action="deleted")
    return delete_file(file_link_id)

@shared_task
def async_delete_folder(folder_id):
    return delete_folder(folder_id)

@shared_task
def async_duplicate_file(file_link_id):
    link = FileFolderLink.objects.get(id=file_link_id)
    new_link = duplicate_file(file_link_id)
    FileAuditLog.objects.create(file=new_link.file, user=new_link.file.user, action="created", notes="Duplicated")
    return {"message": f"Duplicated file {link.file.filename}", "new_file_id": new_link.file.id}

@shared_task
def async_copy_file(file_id, destination_folder_id):
    new_link = copy_file(file_id, destination_folder_id)
    FileAuditLog.objects.create(file=new_link.file, user=new_link.file.user, action="created", notes="Copied to another folder")
    return {"message": f"Copied file to folder {new_link.folder.name}", "file_id": new_link.file.id}

@shared_task
def async_zip_files(file_ids):
    return zip_files(file_ids)

@shared_task
def async_password_protect_file(file_link_id, password_hint):
    result = protect_file_with_password(file_link_id, password_hint)
    link = FileFolderLink.objects.get(id=file_link_id)
    FileAuditLog.objects.create(file=link.file, user=link.file.user, action="updated", notes="Password protected")
    return result

@shared_task
def async_restore_file(file_link_id):
    link = FileFolderLink.objects.get(id=file_link_id)
    result = restore_file_from_trash(file_link_id)
    FileAuditLog.objects.create(file=link.file, user=link.file.user, action="restored")
    return result

@shared_task
def async_restore_folder(folder_id):
    return restore_folder_from_trash(folder_id)

@shared_task
def async_create_file_version(file_id, new_path, user_id):
    file = File.objects.get(pk=file_id)
    user = User.objects.get(pk=user_id)

    latest_version = file.versions.aggregate(max_version=models.Max('version_number'))['max_version'] or 0
    FileVersion.objects.create(
        file=file,
        version_number=latest_version + 1,
        file_path=new_path,
        uploaded_by=user
    )
    FileAuditLog.objects.create(file=file, user=user, action="updated", notes=f"Version {latest_version + 1} saved")
    return {"message": f"Version {latest_version + 1} created", "file_id": file_id}

