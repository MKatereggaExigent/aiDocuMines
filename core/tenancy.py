from django.shortcuts import get_object_or_404
from rest_framework.views import APIView


class ClientScopedViewMixin(APIView):
    """
    Mixin that automatically scopes queryset lookups to the authenticated user's client.
    Override `get_client_scoped_queryset()` to define the base queryset.
    """

    client_scope_field = "user__client"

    def get_client(self):
        return getattr(self.request.user, "client", None)

    def get_client_scoped_queryset(self, queryset):
        client = self.get_client()
        if client is None:
            return queryset.none()
        return queryset.filter(**{self.client_scope_field: client})

    def get_object_by_client(self, queryset, **lookup_kwargs):
        client = self.get_client()
        if client is None:
            from rest_framework.exceptions import NotFound
            raise NotFound("User has no client")
        return get_object_or_404(queryset, **lookup_kwargs, **{self.client_scope_field: client})
