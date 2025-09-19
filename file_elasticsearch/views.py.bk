# file_elasticsearch/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from . import utils
from .serializers import SearchRequestSerializer, AdvancedSearchSerializer
from .tasks import reindex_files_task

class DeleteIndexView(APIView):
    def post(self, request):
        utils.delete_index()
        return Response({"message": "Index deleted."})

class ForceReindexView(APIView):
    def post(self, request):
        reindex_files_task.delay()
        return Response({"message": "Reindex started."})

class IndexSingleFileView(APIView):
    def post(self, request, file_id):
        from core.models import File
        try:
            file = File.objects.get(id=file_id)
            utils.index_file(file)
            return Response({"message": f"File {file_id} indexed."})
        except File.DoesNotExist:
            return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)

class SearchView(APIView):
    def post(self, request):
        serializer = SearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = serializer.validated_data.get('query')
        scope = serializer.validated_data.get('scope', 'both')
        results = utils.basic_search(query, scope)
        return Response([hit.to_dict() for hit in results])

class AdvancedSearchView(APIView):
    def post(self, request):
        serializer = AdvancedSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        results = utils.advanced_search(
            must=serializer.validated_data.get('must'),
            filter=serializer.validated_data.get('filter')
        )
        return Response([hit.to_dict() for hit in results])

