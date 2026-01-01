from rest_framework import serializers
from .models import Folder, FileFolderLink, EffectiveAccess, FileVersion
from core.models import File
from django.contrib.auth import get_user_model

User = get_user_model()

class FolderSerializer(serializers.ModelSerializer):
    subfolders = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Folder
        fields = "__all__"


class FileFolderLinkSerializer(serializers.ModelSerializer):
    file_name = serializers.CharField(source='file.filename', read_only=True)
    file_id = serializers.IntegerField(source='file.id', read_only=True)
    file_size = serializers.IntegerField(source='file.file_size', read_only=True)
    file_type = serializers.CharField(source='file.file_type', read_only=True)
    created_at = serializers.DateTimeField(source='file.created_at', read_only=True)
    updated_at = serializers.DateTimeField(source='file.updated_at', read_only=True)
    shared_with = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = FileFolderLink
        fields = [
            'id', 'file_id', 'file_name', 'file_size', 'file_type',
            'folder', 'is_trashed', 'is_shared', 'password_protected',
            'password_hint', 'shared_with', 'created_at', 'updated_at',
            'download_url'
        ]

    def get_download_url(self, obj):
        """Generate download URL for the file"""
        if obj.file and obj.file.filepath:
            # Return the filepath as the download URL
            # The frontend will use this to construct the full download URL
            return obj.file.filepath
        return None

    def get_shared_with(self, obj):
        access_entries = obj.access_entries.select_related('user').all()
        return [
            {
                "user_id": entry.user.id,
                "email": entry.user.email,
                "can_read": entry.can_read,
                "can_write": entry.can_write,
                "can_delete": entry.can_delete,
                "can_share": entry.can_share,
            }
            for entry in access_entries if entry.user
        ]


class FileSerializer(serializers.ModelSerializer):
    folder_link = FileFolderLinkSerializer(read_only=True)

    class Meta:
        model = File
        fields = [
            'id', 'filename', 'filepath', 'file_size',
            'file_type', 'status', 'folder_link',
        ]


class EffectiveAccessSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = EffectiveAccess
        fields = "__all__"


class FileVersionSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)

    class Meta:
        model = FileVersion
        fields = [
            'version_number',
            'file_path',
            'uploaded_at',
            'uploaded_by_email',
        ]



class RecursiveFolderSerializer(serializers.ModelSerializer):
    subfolders = serializers.SerializerMethodField()
    files      = serializers.SerializerMethodField()

    class Meta:
        model  = Folder
        fields = [
            "id", "name", "project_id", "service_id", "parent",
            "created_at", "is_trashed", "is_protected", "subfolders", "files",
        ]

    # ──────────────────────────────────────────
    def get_subfolders(self, obj):
        children = obj.subfolders.all().order_by("name")
        # pass self.context to keep request in nested levels
        return RecursiveFolderSerializer(
            children, many=True, context=self.context
        ).data

    def get_files(self, obj):
        if not self.context.get("include_files", True):
            return []

        # Respect include_trashed context parameter
        include_trashed = self.context.get("include_trashed", False)
        if include_trashed:
            links = obj.files.all().select_related("file")
        else:
            links = obj.files.filter(is_trashed=False).select_related("file")

        # forward context here as well
        return FileFolderLinkSerializer(
            links, many=True, context=self.context
        ).data




'''
class RecursiveFolderSerializer(serializers.ModelSerializer):
    subfolders = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = [
            'id', 'name', 'project_id', 'service_id', 'parent',
            'created_at', 'subfolders', 'files'
        ]

    def get_subfolders(self, obj):
        # Use reverse relation 'subfolders' or 'children' depending on your related_name
        children = obj.subfolders.all().order_by("name")  # adjust if your related_name differs
        return RecursiveFolderSerializer(children, many=True, context=self.context).data

    def get_files(self, obj):
        include = self.context.get("include_files", True)
        if not include:
            return []

        # Avoid returning trashed or unrelated files
        links = obj.filefolderlink_set.filter(is_trashed=False).select_related("file")
        return FileFolderLinkSerializer(links, many=True).data
'''
