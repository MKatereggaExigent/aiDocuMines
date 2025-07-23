# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Folder, FileFolderLink
from .serializers import (
    FolderSerializer, FileFolderLinkSerializer,
    FileSerializer, EffectiveAccessSerializer, RecursiveFolderSerializer
)
from core.models import File
from custom_authentication.permissions import IsOwner, HasEffectiveAccess
from .tasks import (
    async_bulk_trash_files,
    async_bulk_move_files_to_folder,
    async_rename_file,
    async_rename_folder,
    async_delete_file,
    async_delete_folder,
    async_duplicate_file,
    async_copy_file,
    async_zip_files,
    async_password_protect_file,
    async_restore_file,
    async_restore_folder,
)

import os
import shutil
from document_operations.models import FileVersion
from django.conf import settings
from rest_framework.generics import RetrieveAPIView
from .models import FileFolderLink
from .serializers import FileFolderLinkSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.contrib.auth.models import Group
from .tasks import async_grant_public_link
from .utils import update_access_level_for_user
from .models import FileAccessEntry
from django.contrib.auth import get_user_model
from document_operations.utils import set_password_protection
from document_operations.models import FileAuditLog
from rest_framework.parsers import JSONParser  # 🔁 Import this at the top

User = get_user_model()

'''
class FolderDetailView(APIView):
    permission_classes = [IsAuthenticated, HasEffectiveAccess]

    def get(self, request, pk):
        folder = get_object_or_404(Folder, pk=pk)
        self.check_object_permissions(request, folder)
        serializer = FolderSerializer(folder)
        return Response(serializer.data)
'''


class FolderDetailView(APIView):
    """
    GET /api/v1/documents/folders/<uuid>/

    Returns full recursive details of a single folder:
    - subfolders (nested)
    - files (optional, default true)

    Query-string support:
    ─────────────────────
    ?include_files=false  → omit the file listings
    """
    permission_classes = [IsAuthenticated, HasEffectiveAccess]

    def get(self, request, pk):
        folder = get_object_or_404(Folder, pk=pk)
        self.check_object_permissions(request, folder)

        include_files = request.query_params.get("include_files", "true").lower() == "true"
        ctx = {"include_files": include_files, "request": request}
        serializer = RecursiveFolderSerializer(folder, context=ctx)

        return Response(serializer.data, status=status.HTTP_200_OK)




class FileDetailView(APIView):
    permission_classes = [IsAuthenticated, HasEffectiveAccess]

    def get(self, request, pk):
        file = get_object_or_404(File, pk=pk)
        self.check_object_permissions(request, file)
        serializer = FileSerializer(file)
        return Response(serializer.data)


class RenameFileView(APIView):
    permission_classes = [IsAuthenticated, IsOwner, HasEffectiveAccess]

    def patch(self, request, pk):
        new_name = request.data.get("new_name")
        if not new_name:
            return Response({"error": "Missing new_name"}, status=400)

        # Audit log
        file_link = get_object_or_404(FileFolderLink, pk=pk)
        FileAuditLog.objects.create(
            file=file_link.file,
            user=request.user,
            action="renamed",
            extra={"new_name": new_name}
        )

        async_rename_file.delay(pk, new_name)
        return Response({"message": "File rename initiated."}, status=202)


class RenameFolderView(APIView):
    permission_classes = [IsAuthenticated, IsOwner, HasEffectiveAccess]

    def patch(self, request, pk):
        new_name = request.data.get("new_name")
        if not new_name:
            return Response({"error": "Missing new_name"}, status=400)

        async_rename_folder.delay(pk, new_name)
        return Response({"message": "Folder rename initiated."}, status=202)


class TrashFilesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_ids = request.data.get("file_ids", [])
        if not file_ids:
            return Response({"error": "Missing file_ids list."}, status=400)

        for fid in file_ids:
            link = get_object_or_404(FileFolderLink, pk=fid)
            self.check_object_permissions(request, link)

        async_bulk_trash_files.delay(file_ids)
        return Response({"message": "Files trash initiated."}, status=202)


class MoveFilesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_ids = request.data.get("file_ids", [])
        target_folder = request.data.get("target_folder")
        if not file_ids or not target_folder:
            return Response({"error": "Missing file_ids or target_folder."}, status=400)

        for fid in file_ids:
            link = get_object_or_404(FileFolderLink, pk=fid)
            self.check_object_permissions(request, link)

        async_bulk_move_files_to_folder.delay(file_ids, target_folder)
        return Response({"message": "Files move initiated."}, status=202)


class DeleteFileView(APIView):
    permission_classes = [IsAuthenticated, IsOwner, HasEffectiveAccess]

    def delete(self, request, pk):
        file_link = get_object_or_404(FileFolderLink, pk=pk)

        FileAuditLog.objects.create(
            file=file_link.file,
            user=request.user,
            action="deleted"
        )

        async_delete_file.delay(pk)
        return Response({"message": "File deletion initiated."}, status=202)


class DeleteFolderView(APIView):
    permission_classes = [IsAuthenticated, IsOwner, HasEffectiveAccess]

    def delete(self, request, pk):
        async_delete_folder.delay(pk)
        return Response({"message": "Folder deletion initiated."}, status=202)


class DuplicateFileView(APIView):
    permission_classes = [IsAuthenticated, IsOwner, HasEffectiveAccess]

    def post(self, request, pk):
        async_duplicate_file.delay(pk)
        return Response({"message": "File duplication initiated."}, status=202)


class CopyFileView(APIView):
    permission_classes = [IsAuthenticated, IsOwner, HasEffectiveAccess]

    def post(self, request, pk):
        target_folder = request.data.get("target_folder")
        if not target_folder:
            return Response({"error": "Missing target_folder"}, status=400)

        async_copy_file.delay(pk, target_folder)
        return Response({"message": "File copy initiated."}, status=202)


class ZipFilesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_ids = request.data.get("file_ids", [])
        if not file_ids:
            return Response({"error": "Missing file_ids"}, status=400)

        async_zip_files.delay(file_ids)
        return Response({"message": "Zip operation initiated."}, status=202)


class ProtectFileView(APIView):
    permission_classes = [IsAuthenticated, HasEffectiveAccess]

    def post(self, request, pk):
        password_hint = request.data.get("password_hint")
        if not password_hint:
            return Response({"error": "Missing password_hint"}, status=400)

        # Audit log
        file_link = get_object_or_404(FileFolderLink, pk=pk)
        FileAuditLog.objects.create(
            file=file_link.file,
            user=request.user,
            action="updated",
            extra={"protection": "password", "hint": password_hint}
        )

        async_password_protect_file.delay(pk, password_hint)
        return Response({"message": "Password protection initiated."}, status=202)


class RestoreFileView(APIView):
    permission_classes = [IsAuthenticated, HasEffectiveAccess]

    def post(self, request, pk):
        file_link = get_object_or_404(FileFolderLink, pk=pk)

        FileAuditLog.objects.create(
            file=file_link.file,
            user=request.user,
            action="restored"
        )

        async_restore_file.delay(pk)
        return Response({"message": "File restore initiated."}, status=202)


class RestoreFolderView(APIView):
    permission_classes = [IsAuthenticated, HasEffectiveAccess]

    def post(self, request, pk):
        async_restore_folder.delay(pk)
        return Response({"message": "Folder restore initiated."}, status=202)


class ListFileVersionsView(APIView):
    permission_classes = [IsAuthenticated, HasEffectiveAccess]

    def get(self, request, pk):
        file = get_object_or_404(File, pk=pk)
        versions = file.versions.all()
        data = [{
            "version": v.version_number,
            "uploaded_at": v.uploaded_at,
            "uploaded_by": v.uploaded_by.email if v.uploaded_by else "Unknown",
            "file_path": v.file_path,
        } for v in versions]
        return Response(data, status=200)


class RestoreFileVersionView(APIView):
    permission_classes = [IsAuthenticated, HasEffectiveAccess]

    def post(self, request, pk, version_number):
        file = get_object_or_404(File, pk=pk)
        self.check_object_permissions(request, file)

        try:
            version = get_object_or_404(file.versions, version_number=version_number)
        except FileVersion.DoesNotExist:
            return Response({"error": "Version not found."}, status=status.HTTP_404_NOT_FOUND)

        # Ensure the source file path exists
        if not os.path.exists(version.file_path):
            return Response({"error": "Version file is missing on disk."}, status=status.HTTP_404_NOT_FOUND)

        # Create a backup of the current file (optional)
        backup_dir = os.path.join(settings.MEDIA_ROOT, "backups", str(file.id))
        os.makedirs(backup_dir, exist_ok=True)

        backup_path = os.path.join(backup_dir, f"backup_{file.filename}")
        if os.path.exists(file.file.path):
            shutil.copy(file.file.path, backup_path)

        try:
            # Restore the selected version (overwrite the current file)
            shutil.copy(version.file_path, file.file.path)
        except Exception as e:
            return Response({"error": f"Restore failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "message": f"Successfully restored file to version {version_number}.",
            "backup_created_at": backup_path
        }, status=status.HTTP_200_OK)


class SharedFilesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        access_links = FileAccessEntry.objects.filter(user=request.user).select_related("file_link__file")
        file_links = [entry.file_link for entry in access_links]
        serializer = FileFolderLinkSerializer(file_links, many=True)
        return Response(serializer.data)


'''
class ShareFileView(APIView):
    permission_classes = [IsAuthenticated, HasEffectiveAccess]

    def post(self, request, pk):
        file_link = get_object_or_404(FileFolderLink, pk=pk)
        self.check_object_permissions(request, file_link)

        user_ids = request.data.get("user_ids", [])
        if not user_ids:
            return Response({"error": "No users provided."}, status=400)

        for uid in user_ids:
            user = get_object_or_404(User, pk=uid)
            file_link.shared_with.add(user)

        file_link.is_shared = True
        file_link.save()

        return Response({"message": "File shared successfully."}, status=200)
'''


class ShareFileView(APIView):
    permission_classes = [IsAuthenticated, HasEffectiveAccess]
    parser_classes = [JSONParser] 

    @swagger_auto_schema(
        operation_description="Share a file with users",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_ids": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER)),
                "access_level": openapi.Schema(type=openapi.TYPE_STRING, enum=["read", "write", "owner"], default="read")
            }
        ),
        responses={200: "Success"}
    )
    def post(self, request, pk):
        file_link = get_object_or_404(FileFolderLink, pk=pk)
        self.check_object_permissions(request, file_link)

        user_ids = request.data.get("user_ids", [])
        level = request.data.get("access_level", "read")

        access_map = {
            "read":  {"can_read": True},
            "write": {"can_read": True, "can_write": True},
            "owner": {"can_read": True, "can_write": True, "can_share": True, "is_owner": True}
        }
        perms = access_map.get(level, {"can_read": True})

        if not user_ids:
            return Response({"error": "No users provided."}, status=400)

        for uid in user_ids:
            user = get_object_or_404(User, pk=uid)
            FileAccessEntry.objects.update_or_create(
                file_link=file_link,
                user=user,
                defaults={**perms, "granted_by": request.user}
            )

        file_link.is_shared = True
        file_link.save()

        return Response({
            "message": "File shared successfully.",
            "shared_with": user_ids,
            "access_level": level
        }, status=200)


class UnshareFileView(APIView):
    permission_classes = [IsAuthenticated, HasEffectiveAccess]

    def post(self, request, pk):
        file_link = get_object_or_404(FileFolderLink, pk=pk)
        self.check_object_permissions(request, file_link)

        FileAccessEntry.objects.filter(file_link=file_link).delete()
        file_link.is_shared = False
        file_link.save()

        return Response({"message": "File unshared successfully."}, status=200)


class FilePreviewView(APIView):
    permission_classes = [IsAuthenticated, HasEffectiveAccess]

    def get(self, request, pk):
        file = get_object_or_404(File, pk=pk)
        self.check_object_permissions(request, file)

        return Response({
            "filename": file.filename,
            "filetype": file.file_type,
            "preview_url": file.file.url,  # or some logic to return base64/image/text preview
        })



class FileAuditLogView(APIView):
    permission_classes = [IsAuthenticated, HasEffectiveAccess]

    def get(self, request, pk):
        # Logs from FileAuditLog model
        logs = FileAuditLog.objects.filter(file_id=pk).order_by("-timestamp")

        # Access entries from sharing
        access_entries = FileAccessEntry.objects.filter(file_link__file_id=pk)

        log_data = [
            {
                "type": "Log",
                "action": log.action,
                "user": log.user.email if log.user else None,
                "extra": log.extra,
                "timestamp": log.timestamp,
            }
            for log in logs
        ]

        access_data = [
            {
                "type": "Access",
                "user": e.user.email,
                "granted_by": e.granted_by.email if e.granted_by else None,
                "access": {
                    "read": e.can_read,
                    "write": e.can_write,
                    "share": e.can_share,
                    "owner": getattr(e, "is_owner", False),  # fallback safe
                },
                "granted_at": e.granted_at,
            }
            for e in access_entries
        ]

        return Response(log_data + access_data, status=200)



'''
class FileAuditLogView(APIView):
    permission_classes = [IsAuthenticated, HasEffectiveAccess]

    def get(self, request, pk):
        logs = FileAuditLog.objects.filter(file_id=pk).order_by("-timestamp")
        access_entries = FileAccessEntry.objects.filter(file_link__file_id=pk)

        access_log_data = [
            {
                "type": "Access",
                "user": e.user.email,
                "granted_by": e.granted_by.email if e.granted_by else None,
                "access": {
                    "read": e.can_read,
                    "write": e.can_write,
                    "share": e.can_share,
                    "owner": e.can_write and e.can_share and not e.expires_at,  # inferred owner
                },
                "granted_at": e.granted_at
            }
            for e in access_entries
        ]

        file_logs = [{
            "type": "Log",
            "action": log.action,
            "user": log.user.email,
            "timestamp": log.timestamp,
        } for log in logs]

        return Response(file_logs + access_log_data, status=200)
'''

class PublicSharedFileView(RetrieveAPIView):
    permission_classes = []  # public access

    def get(self, request, share_token):
        link = get_object_or_404(FileFolderLink, public_token=share_token, is_public=True)
        serializer = FileFolderLinkSerializer(link)
        return Response({
            "shared_file": serializer.data,
            "preview_url": link.file.file.url  # Optional: direct link
        })

'''
# document_operations/views.py
class FolderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        folders = Folder.objects.filter(user=request.user)
        data = [{"id": str(f.id), "name": f.name, "project_id": f.project_id} for f in folders]
        return Response(data)
'''

# document_operations/views.py
class FolderListView(APIView):
    """
    GET /api/v1/documents/folders/

    Query-string filters
    ─────────────────────
    ?project_id=<str>      → return only this project’s root folders
    ?service_id=<str>      → narrow further by service
    ?include_trashed=true  → include folders that are in the trash
    ?include_files=false   → omit the file listings inside each folder
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # ── base queryset: current user + root-level folders
        qs = Folder.objects.filter(user=request.user, parent__isnull=True)

        # ── optional query-string filters
        project_id      = request.query_params.get("project_id")
        service_id      = request.query_params.get("service_id")
        include_trashed = request.query_params.get("include_trashed", "false").lower() == "true"
        include_files   = request.query_params.get("include_files",  "true").lower() == "true"

        if project_id:
            qs = qs.filter(project_id=project_id)

        if service_id:
            qs = qs.filter(service_id=service_id)

        if not include_trashed:
            qs = qs.filter(is_trashed=False)

        # ── serializer context lets us tell the recursive serializer
        #    whether to include the file list for each folder.
        ctx = {"include_files": include_files, "request": request}

        serializer = RecursiveFolderSerializer(qs, many=True, context=ctx)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FolderCreateView(APIView):
    """
    POST /api/v1/documents/folders/

    Body:
    {
      "name": "child_folder",
      "project_id": "test_project",
      "service_id": "test_service",
      "parent": "<optional_parent_uuid>"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        data['user'] = request.user.id  # bind folder to user

        serializer = FolderSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        folder = serializer.save()
        return Response(FolderSerializer(folder).data, status=status.HTTP_201_CREATED)




class TrashSingleFileView(APIView):
    """
    PATCH /api/v1/documents/files/<pk>/trash/

    Moves a single file to trash.
    """
    permission_classes = [IsAuthenticated, HasEffectiveAccess]

    def patch(self, request, pk):
        file = get_object_or_404(File, pk=pk)
        self.check_object_permissions(request, file)
        file.is_trashed = True
        file.save()
        return Response({"message": f"File {pk} moved to trash."}, status=200)



class FolderListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Folder.objects.filter(user=request.user, parent__isnull=True)

        project_id      = request.query_params.get("project_id")
        service_id      = request.query_params.get("service_id")
        include_trashed = request.query_params.get("include_trashed", "false").lower() == "true"
        include_files   = request.query_params.get("include_files",  "true").lower() == "true"

        if project_id:
            qs = qs.filter(project_id=project_id)

        if service_id:
            qs = qs.filter(service_id=service_id)

        if not include_trashed:
            qs = qs.filter(is_trashed=False)

        ctx = {"include_files": include_files, "request": request}
        serializer = RecursiveFolderSerializer(qs, many=True, context=ctx)
        return Response(serializer.data, status=200)

    def post(self, request):
        data = request.data.copy()
        data['user'] = request.user.id
        serializer = FolderSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        folder = serializer.save()
        return Response(FolderSerializer(folder).data, status=201)



class ShareWithGroupView(APIView):
    permission_classes = [IsAuthenticated, HasEffectiveAccess]

    @swagger_auto_schema(
        operation_description="Share file with a group",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "group_name": openapi.Schema(type=openapi.TYPE_STRING),
                "access_level": openapi.Schema(type=openapi.TYPE_STRING, enum=["read", "write", "owner"]),
            }
        ),
        responses={200: "Shared successfully"}
    )
    def post(self, request, pk):
        file_link = get_object_or_404(FileFolderLink, pk=pk)
        self.check_object_permissions(request, file_link)

        group_name = request.data.get("group_name")
        level = request.data.get("access_level", "read")
        group = get_object_or_404(Group, name=group_name)

        perms = {
            "read":  {"can_read": True},
            "write": {"can_read": True, "can_write": True},
            "owner": {"can_read": True, "can_write": True, "can_share": True, "is_owner": True}
        }.get(level, {"can_read": True})

        for user in group.user_set.all():
            FileAccessEntry.objects.update_or_create(
                file_link=file_link,
                user=user,
                defaults={**perms, "granted_by": request.user}
            )

        file_link.is_shared = True
        file_link.save()

        return Response({"message": f"Shared with group {group_name}"}, status=200)


class SetAccessLevelView(APIView):
    permission_classes = [IsAuthenticated, HasEffectiveAccess]

    @swagger_auto_schema(
        operation_description="Update a user's access level for a file",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "access_level": openapi.Schema(type=openapi.TYPE_STRING, enum=["read", "write", "owner"]),
            }
        ),
        responses={200: "Updated"}
    )
    def patch(self, request, pk):
        file_link = get_object_or_404(FileFolderLink, pk=pk)
        self.check_object_permissions(request, file_link)

        user_id = request.data.get("user_id")
        level = request.data.get("access_level", "read")

        result = update_access_level_for_user(file_link, user_id, level, request.user)
        return Response(result, status=200)


class GrantPublicLinkView(APIView):
    permission_classes = [IsAuthenticated, HasEffectiveAccess]

    def post(self, request, pk):
        file_link = get_object_or_404(FileFolderLink, pk=pk)
        self.check_object_permissions(request, file_link)

        FileAuditLog.objects.create(
            file=file_link.file,
            user=request.user,
            action="shared",
            extra={"shared_as": "public"}
        )

        async_grant_public_link.delay(file_link.id)
        return Response({"message": "Public access link is being generated."}, status=202)

