import os
import shutil
import zipfile
from django.conf import settings
from core.models import File
from .models import Folder, FileFolderLink, FileVersion, FileAuditLog
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
import uuid
import secrets

User = get_user_model()


def get_folder_upload_path(user_id, client_id, project_id, service_id, run_id, subfolder=None):
    base_path = os.path.join(settings.MEDIA_ROOT, "uploads", str(user_id), client_id, project_id, service_id, str(run_id))
    return os.path.join(base_path, subfolder) if subfolder else base_path


# 📁 Folder Operations
def rename_folder(folder: Folder, new_name: str):
    folder.name = new_name
    folder.save()
    return folder


def trash_folder(folder: Folder):
    folder.is_trashed = True
    folder.save()
    for file in folder.files.all():
        file.is_trashed = True
        file.save()


def restore_folder_from_trash(folder_id):
    folder = Folder.objects.get(id=folder_id)
    folder.is_trashed = False
    folder.save()
    for link in folder.files.all():
        link.is_trashed = False
        link.save()
    return {"message": f"Restored folder {folder.name}"}


def delete_folder(folder: Folder):
    folder.delete()


# 📄 File Operations
def rename_file(file_id, new_name):
    file = File.objects.get(id=file_id)

    old_path = file.filepath
    dir_path = os.path.dirname(old_path)
    new_path = os.path.join(dir_path, new_name)

    # Physically rename the file on disk
    if os.path.exists(old_path):
        os.rename(old_path, new_path)

    # Update the model fields
    file.filename = new_name
    file.filepath = new_path
    file.save()

    return {"message": f"File renamed to {new_name}", "file_id": file.id}


def move_file_to_folder(file_link: FileFolderLink, new_folder: Folder):
    file_link.folder = new_folder
    file_link.save()
    return file_link


def restore_file_from_trash(file_link_id):
    link = FileFolderLink.objects.get(id=file_link_id)
    link.is_trashed = False
    link.save()
    return {"message": f"Restored file {link.file.filename}"}


def delete_file(file_link_id):
    link = FileFolderLink.objects.get(id=file_link_id)
    file = link.file
    file.delete()
    link.delete()
    return {"message": f"Deleted file {file_link_id}"}


def copy_file(file_id, destination_folder_id):
    file = File.objects.get(id=file_id)
    folder = Folder.objects.get(id=destination_folder_id)
    new_file = File.objects.create(
        filename=f"{file.filename}_copy",
        filepath=file.filepath,
        file_size=file.file_size,
        file_type=file.file_type,
        md5_hash=None,
        run=file.run,
        user=file.user,
        project_id=file.project_id,
        service_id=file.service_id,
        status="Pending",
    )
    return FileFolderLink.objects.create(file=new_file, folder=folder)


def duplicate_file(file_link_id):
    link = FileFolderLink.objects.get(id=file_link_id)
    return copy_file(link.file.id, link.folder.id)


def zip_files(file_link_ids):
    zip_name = f"archive_{uuid.uuid4()}.zip"
    target_dir = os.path.join(settings.MEDIA_ROOT, "zips")
    os.makedirs(target_dir, exist_ok=True)
    zip_path = os.path.join(target_dir, zip_name)
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for link_id in file_link_ids:
            link = FileFolderLink.objects.get(id=link_id)
            zf.write(link.file.filepath, arcname=link.file.filename)
    return {"zip_path": zip_path, "zip_name": zip_name}


def protect_file_with_password(file_link_id, password_hint):
    link = FileFolderLink.objects.get(id=file_link_id)
    link.password_protected = True
    link.password_hint = password_hint
    link.save()
    return {"message": f"File {link.file.filename} password protected."}


# 🔄 Bulk Operations
def move_files_to_trash(file_link_ids):
    count = 0
    for link_id in file_link_ids:
        link = FileFolderLink.objects.filter(id=link_id).first()
        if link:
            link.is_trashed = True
            link.save()
            count += 1
    return count


def reassign_folder_for_files(file_link_ids, new_folder):
    updated_links = []
    with transaction.atomic():
        for link_id in file_link_ids:
            link = FileFolderLink.objects.filter(id=link_id).first()
            if link:
                link.folder = new_folder
                link.save()
                updated_links.append(link)
    return updated_links


# 📜 File Versioning
def create_file_version(file: File, uploaded_by=None):
    latest_version = file.versions.first()
    new_version = (latest_version.version_number + 1) if latest_version else 1

    version_path = os.path.join(settings.MEDIA_ROOT, "versions", str(file.id), f"v{new_version}")
    os.makedirs(os.path.dirname(version_path), exist_ok=True)
    shutil.copy(file.file.path, version_path)

    return FileVersion.objects.create(
        file=file,
        version_number=new_version,
        file_path=version_path,
        uploaded_by=uploaded_by
    )


# 🔗 Sharing
def generate_share_token():
    return secrets.token_urlsafe(32)


def generate_public_link(file_link: FileFolderLink):
    if not file_link.public_token:
        file_link.public_token = generate_share_token()
        file_link.shared_link_created_at = timezone.now()
        file_link.is_public = True
        file_link.save()
    return file_link.public_token


def revoke_public_link(file_link: FileFolderLink):
    file_link.public_token = None
    file_link.is_public = False
    file_link.shared_link_created_at = None
    file_link.save()


# 🕵️ Logging
def log_file_activity(file: File, user: User, action: str, notes=None):
    FileAuditLog.objects.create(file=file, user=user, action=action, notes=notes)

