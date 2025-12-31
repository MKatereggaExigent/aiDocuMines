# file_elasticsearch/views.py

import time
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from oauth2_provider.contrib.rest_framework import OAuth2Authentication

from . import utils
from .serializers import SearchRequestSerializer, AdvancedSearchSerializer
from .tasks import reindex_files_task

from document_operations.utils import get_user_accessible_file_ids
from core.models import File, Run
from document_operations.models import FileAccessEntry
from core.utils import generate_and_register_service_report

logger = logging.getLogger(__name__)

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
    permission_classes = [IsAuthenticated]

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
    """
    Elasticsearch basic search.
    POST /api/v1/es/search/
    body: {
        "query": "search term",
        "scope": "both" | "filename" | "content",
        "project_id": optional (for report registration),
        "service_id": optional (for report registration),
        "generate_report": optional (default: false)
    }
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        start_time = time.time()
        serializer = SearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data.get("query")
        scope = serializer.validated_data.get("scope", "both")

        # New parameters for report generation
        project_id = request.data.get("project_id")
        service_id = request.data.get("service_id")
        generate_report = request.data.get("generate_report", False)

        accessible_ids = get_user_accessible_file_ids(request.user)
        results = utils.basic_search(
            query=query,
            scope=scope,
            user=request.user,
            accessible_ids=accessible_ids,
        )

        execution_time = time.time() - start_time
        results_list = [hit.to_dict() for hit in results]

        response_data = {
            "results": results_list,
            "count": len(results_list),
            "query": query,
            "scope": scope,
            "execution_time_seconds": round(execution_time, 2)
        }

        # Generate and register report if requested
        if generate_report and project_id and service_id:
            try:
                run = Run.objects.create(
                    user=request.user,
                    project_id=project_id,
                    service_id=service_id,
                    status="completed",
                    result_json=response_data
                )

                report_info = generate_and_register_service_report(
                    service_name="Elasticsearch Search",
                    service_id="ai-elasticsearch-search",
                    vertical="AI Services",
                    response_data=response_data,
                    user=request.user,
                    run=run,
                    project_id=project_id,
                    service_id_folder=service_id,
                    folder_name="elasticsearch-search-results",
                    query=query,
                    execution_time_seconds=execution_time,
                    additional_metadata={
                        "scope": scope,
                        "result_count": len(results_list)
                    }
                )
                response_data["report_file"] = report_info
                logger.info(f"✅ Generated ES search report: {report_info.get('filename')}")
            except Exception as report_error:
                logger.warning(f"Failed to generate report: {report_error}")
                response_data["report_error"] = str(report_error)

        return Response(response_data)


class AdvancedSearchView(APIView):
    """
    Elasticsearch advanced search.
    POST /api/v1/es/advanced-search/
    body: {
        "must": [...],
        "filter": [...],
        "project_id": optional (for report registration),
        "service_id": optional (for report registration),
        "generate_report": optional (default: false)
    }
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        start_time = time.time()
        serializer = AdvancedSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # New parameters for report generation
        project_id = request.data.get("project_id")
        service_id = request.data.get("service_id")
        generate_report = request.data.get("generate_report", False)

        accessible_ids = get_user_accessible_file_ids(request.user)
        results = utils.advanced_search(
            must=serializer.validated_data.get("must"),
            filter=serializer.validated_data.get("filter"),
            user=request.user,
            accessible_ids=accessible_ids,
        )

        execution_time = time.time() - start_time
        results_list = [hit.to_dict() for hit in results]

        response_data = {
            "results": results_list,
            "count": len(results_list),
            "execution_time_seconds": round(execution_time, 2)
        }

        # Generate and register report if requested
        if generate_report and project_id and service_id:
            try:
                run = Run.objects.create(
                    user=request.user,
                    project_id=project_id,
                    service_id=service_id,
                    status="completed",
                    result_json=response_data
                )

                report_info = generate_and_register_service_report(
                    service_name="Elasticsearch Advanced Search",
                    service_id="ai-elasticsearch-advanced-search",
                    vertical="AI Services",
                    response_data=response_data,
                    user=request.user,
                    run=run,
                    project_id=project_id,
                    service_id_folder=service_id,
                    folder_name="elasticsearch-advanced-search-results",
                    execution_time_seconds=execution_time,
                    additional_metadata={
                        "result_count": len(results_list)
                    }
                )
                response_data["report_file"] = report_info
                logger.info(f"✅ Generated ES advanced search report: {report_info.get('filename')}")
            except Exception as report_error:
                logger.warning(f"Failed to generate report: {report_error}")
                response_data["report_error"] = str(report_error)

        return Response(response_data)

