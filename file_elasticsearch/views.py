# file_elasticsearch/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from custom_authentication.permissions import IsClientOrAdminOrSuperUser

from . import utils
from .serializers import SearchRequestSerializer, AdvancedSearchSerializer
from .tasks import reindex_files_task

from document_operations.utils import get_user_accessible_file_ids
from core.models import File
from document_operations.models import FileAccessEntry

class DeleteIndexView(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAdminUser]

    def post(self, request):
        utils.delete_index()
        return Response({"message": "Index deleted."})

class ForceReindexView(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAdminUser]

    def post(self, request):
        reindex_files_task.delay()
        return Response({"message": "Reindex started."})

class IndexSingleFileView(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated, IsClientOrAdminOrSuperUser]

    def post(self, request, file_id):
        try:
            file = File.objects.get(id=file_id)
        except File.DoesNotExist:
            return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)

        # allow if owner or explicitly shared (read is enough for indexing its text)
        is_owner = file.user_id == request.user.id
        is_shared = FileAccessEntry.objects.filter(file_id=file_id, user=request.user, can_read=True).exists()
        if not (is_owner or is_shared):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        utils.index_file(file)
        return Response({"message": f"File {file_id} indexed."})

class SearchView(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated, IsClientOrAdminOrSuperUser]

    def post(self, request):
        serializer = SearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data.get("query")
        scope = serializer.validated_data.get("scope", "both")

        accessible_ids = get_user_accessible_file_ids(request.user)
        results = utils.basic_search(
            query=query,
            scope=scope,
            user=request.user,
            accessible_ids=accessible_ids,
        )
        # Optionally trim fields to avoid returning full content
        return Response([hit.to_dict() for hit in results])

class AdvancedSearchView(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated, IsClientOrAdminOrSuperUser]

    def post(self, request):
        serializer = AdvancedSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        accessible_ids = get_user_accessible_file_ids(request.user)
        results = utils.advanced_search(
            must=serializer.validated_data.get("must"),
            filter=serializer.validated_data.get("filter"),
            user=request.user,
            accessible_ids=accessible_ids,
        )
        return Response([hit.to_dict() for hit in results])

