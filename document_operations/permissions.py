# permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import EffectiveAccess, FileFolderLink, Folder
from core.models import File


class IsOwner(BasePermission):
    """Allows access only to the owner of the file or folder."""
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'file'):
            return obj.file.user == request.user
        return False


class HasEffectiveAccess(BasePermission):
    """Checks if user has access rights on a given File or Folder."""
    def has_object_permission(self, request, view, obj):
        access = None
        if isinstance(obj, Folder):
            access = EffectiveAccess.objects.filter(user=request.user, folder=obj).first()
        elif isinstance(obj, File):
            access = EffectiveAccess.objects.filter(user=request.user, file=obj).first()
        elif isinstance(obj, FileFolderLink):
            access = EffectiveAccess.objects.filter(user=request.user, file=obj.file).first()

        if not access:
            return False

        method_map = {
            'GET': 'can_download',
            'POST': 'can_share',
            'PUT': 'can_rename',
            'PATCH': 'can_move',
            'DELETE': 'can_delete'
        }
        required = method_map.get(request.method, None)
        return getattr(access, required, False) if required else True


class IsReadOnly(BasePermission):
    """Allows only read-only access."""
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS

