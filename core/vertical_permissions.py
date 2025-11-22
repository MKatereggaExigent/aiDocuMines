"""
Base permission classes for vertical apps (Private Equity, Class Actions, etc.)
Provides multi-tenancy and RBAC support.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsClientMember(BasePermission):
    """
    Ensures the user belongs to a client and can only access their client's data.
    This is the base permission for all vertical apps.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'client') and
            request.user.client is not None
        )
    
    def has_object_permission(self, request, view, obj):
        """Ensure object belongs to user's client"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if object has client field
        if hasattr(obj, 'client'):
            return obj.client == request.user.client
        
        # Check if object has user field with client
        if hasattr(obj, 'user') and hasattr(obj.user, 'client'):
            return obj.user.client == request.user.client
        
        return False


class IsClientAdmin(BasePermission):
    """
    User must be an admin within their client organization.
    Admins can manage all data within their client.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'client') and
            request.user.client is not None and
            (request.user.is_staff or request.user.groups.filter(name='Admin').exists())
        )


class IsClientAdminOrReadOnly(BasePermission):
    """
    Admins can do anything, regular users can only read.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'client') or request.user.client is None:
            return False
        
        # Read permissions for all authenticated client members
        if request.method in SAFE_METHODS:
            return True
        
        # Write permissions only for admins
        return request.user.is_staff or request.user.groups.filter(name='Admin').exists()


class IsOwnerOrClientAdmin(BasePermission):
    """
    Object owner or client admin can modify.
    Others in same client can read.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'client') and
            request.user.client is not None
        )
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check client membership first
        obj_client = None
        if hasattr(obj, 'client'):
            obj_client = obj.client
        elif hasattr(obj, 'user') and hasattr(obj.user, 'client'):
            obj_client = obj.user.client
        
        if obj_client != request.user.client:
            return False
        
        # Read permissions for same client
        if request.method in SAFE_METHODS:
            return True
        
        # Write permissions for owner or admin
        is_owner = hasattr(obj, 'user') and obj.user == request.user
        is_admin = request.user.is_staff or request.user.groups.filter(name='Admin').exists()
        
        return is_owner or is_admin


class IsSuperUserOrClientAdmin(BasePermission):
    """
    Superuser can access everything.
    Client admin can access their client's data.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        return (
            hasattr(request.user, 'client') and
            request.user.client is not None and
            (request.user.is_staff or request.user.groups.filter(name='Admin').exists())
        )

