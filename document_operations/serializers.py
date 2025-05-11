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
    shared_with = serializers.SlugRelatedField(
        many=True, slug_field="email", read_only=True
    )

    class Meta:
        model = FileFolderLink
        fields = [
            'id', 'file_id', 'file_name', 'folder', 'is_trashed',
            'is_shared', 'password_protected', 'password_hint',
            'shared_with'
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

