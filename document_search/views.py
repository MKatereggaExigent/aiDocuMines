# document_search/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from django.shortcuts import get_object_or_404
from pymilvus import Collection, connections
from sentence_transformers import SentenceTransformer

from rest_framework.permissions import IsAuthenticated
from oauth2_provider.contrib.rest_framework import OAuth2Authentication

from django.core.cache import cache

from celery.result import AsyncResult

from document_search.models import VectorChunk
from document_search.serializers import (
    SearchRequestSerializer,
    SearchResultSerializer,
    VectorChunkSerializer,
    IndexRequestSerializer,
    AsyncSearchResponse
)
from core.models import File  # adjust to your actual File model path
from document_search.utils import _get_model

from document_search.tasks import (
    index_file,                      #  ← already defined in tasks.py
    bulk_reindex,                    #  ← already defined in tasks.py
)

from document_search.tasks import exec_search 

import time

from django.db.models import Q
from datetime import datetime

from document_search.tasks import semantic_search_task 

import logging

from document_search.config import COLLECTION_NAME

from document_operations.utils import get_user_accessible_file_ids

from document_operations.models import FileAccessEntry

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# 🧠  Connect to Milvus collection
# ─────────────────────────────────────────────────────────────
def _get_collection() -> Collection:
    connections.connect(alias="default", host="localhost", port="19530")
    # collection = Collection("vector_chunks")  # must match tasks.py
    collection = Collection(COLLECTION_NAME)
    collection.load()
    return collection

# -------------------------------------------------------------
# Semantic File Search
# -------------------------------------------------------------
class SemanticFileSearchView(APIView):
    """
    Search using semantic embeddings (vector search in Milvus).
    POST /api/v1/document-search/semantic-search/
    body: {"query": "data science", "top_k": 5, "file_id": optional, "filters": optional}
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        query = request.data.get("query")
        top_k = int(request.data.get("top_k", 5))
        file_id = request.data.get("file_id")
        filters = request.data.get("filters", {})

        if not query:
            return Response({"error": "Query is required"}, status=400)

        # ✅ Determine file scope: only owned/shared files
        accessible_file_ids = get_user_accessible_file_ids(user)

        # Optional narrowing to single file
        if file_id and int(file_id) not in accessible_file_ids:
            return Response({"error": "You do not have access to this file."}, status=403)

        # Enqueue the Celery task
        # task = semantic_search_task.apply_async(args=[user.id, query, top_k, file_id, filters])

        # Enqueue Celery task with access scope
        task = semantic_search_task.apply_async(
                 args=[user.id, query, top_k, file_id, filters, accessible_file_ids]
                 )

        # Respond with task ID for the client to poll for results
        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)


# ─────────────────────────────────────────────────────────────
# 🔍 Search API
# ─────────────────────────────────────────────────────────────
class ChunkedFileSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SearchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        query = serializer.validated_data["query"]
        file_id = serializer.validated_data.get("file_id")
        top_k = serializer.validated_data["top_k"]

        # ✅ Embed query
        embed_model = _get_model()
        query_vector = embed_model.encode([query])[0]

        # ✅ Setup Milvus
        collection = _get_collection()

        # ✅ Get file access scope
        accessible_file_ids = get_user_accessible_file_ids(user)

        # If filtering by file_id, validate access
        expr = ""
        if file_id:
            if file_id not in accessible_file_ids:
                return Response({"error": "You do not have access to this file."}, status=403)
            expr = f"file_id == {file_id}"
        else:
            # Otherwise limit to all files user can access
            if not accessible_file_ids:
                return Response([], status=200)
            id_list = ",".join(map(str, accessible_file_ids))
            expr = f"file_id in [{id_list}]"

        try:
            results = collection.search(
                data=[query_vector],
                anns_field="vector",
                param={"metric_type": "COSINE", "params": {"nprobe": 10}},
                limit=top_k,
                expr=expr,
                output_fields=["file_id", "chunk_text"],
            )
        except Exception as e:
            logger.exception("Search failed")
            return Response({"error": str(e)}, status=500)

        top_matches = []
        for hit in results[0]:
            chunk_text = hit.entity.get("chunk_text", "")
            file_id = hit.entity.get("file_id")
            if file_id not in accessible_file_ids:
                continue  # Skip unauthorized entries (paranoia mode)
            try:
                file_obj = File.objects.get(id=file_id)
            except File.DoesNotExist:
                continue

            top_matches.append({
                "file_id": file_obj.id,
                "file_name": getattr(file_obj, "filename", str(file_obj)),
                "chunk_text": chunk_text,
                "score": hit.score
            })

        response = SearchResultSerializer(top_matches, many=True)
        return Response(response.data, status=200)


'''
class ChunkedFileSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SearchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        query = serializer.validated_data["query"]
        file_id = serializer.validated_data.get("file_id")
        top_k = serializer.validated_data["top_k"]

        # Embed query
        embed_model = _get_model()
        query_vector = embed_model.encode([query])[0]

        # Setup Milvus
        collection = _get_collection()

        # If filtering by file_id
        expr = ""
        if file_id:
            try:
                file_obj = File.objects.get(id=file_id, uploaded_by=user)
            except File.DoesNotExist:
                return Response({"error": "File not found or unauthorized"}, status=404)
            expr = f"file_id == {file_id}"

        try:
            results = collection.search(
                data=[query_vector],
                anns_field="vector",
                param={"metric_type": "COSINE", "params": {"nprobe": 10}},
                limit=top_k,
                expr=expr,
                output_fields=["file_id", "chunk_text"],
            )
        except Exception as e:
            logger.exception("Search failed")
            return Response({"error": str(e)}, status=500)

        top_matches = []
        for hit in results[0]:
            chunk_text = hit.entity.get("chunk_text", "")
            file_id = hit.entity.get("file_id")
            try:
                file_obj = File.objects.get(id=file_id)
            except File.DoesNotExist:
                continue

            top_matches.append({
                "file_id": file_obj.id,
                "file_name": file_obj.filename if hasattr(file_obj, "filename") else str(file_obj),
                "chunk_text": chunk_text,
                "score": hit.score
            })

        response = SearchResultSerializer(top_matches, many=True)
        return Response(response.data, status=200)
'''

# ─────────────────────────────────────────────────────────────
# 🧩 Admin/debug view for inspecting vector chunks
# ─────────────────────────────────────────────────────────────
class VectorChunkListView(generics.ListAPIView):
    queryset = VectorChunk.objects.all().select_related("file")
    serializer_class = VectorChunkSerializer
    permission_classes = [permissions.IsAdminUser]

# ─────────────────────────────────────────────────────────────
# ⚙️  Trigger (re)indexing API
# ─────────────────────────────────────────────────────────────
class TriggerVectorIndexingView(APIView):
    """
    POST  /api/v1/document-search/index/
    body: {"file_ids": [2, 3, 4], "force": false}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = IndexRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        file_ids = ser.validated_data["file_ids"]
        force = ser.validated_data["force"]

        # ✅ Restrict to accessible file IDs
        allowed_ids = set(get_user_accessible_file_ids(request.user))
        filtered_ids = [fid for fid in file_ids if fid in allowed_ids]

        if not filtered_ids:
            return Response({"error": "No valid files to index."}, status=403)

        for fid in filtered_ids:
            index_file.delay(fid, force=force)

        return Response(
            {
                "queued": len(filtered_ids),
                "force": force,
                "file_ids": filtered_ids,
            },
            status=status.HTTP_202_ACCEPTED,
        )


'''
class TriggerVectorIndexingView(APIView):
    """
    POST  /api/v1/document-search/index/
    body: {"file_ids": [2, 3, 4], "force": false}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = IndexRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        file_ids = ser.validated_data["file_ids"]
        force = ser.validated_data["force"]

        # Fire-and-forget: enqueue a Celery task per File
        for fid in file_ids:
            index_file.delay(fid, force=force)   # async

        return Response(
            {
                "queued": len(file_ids),
                "force": force,
                "file_ids": file_ids,
            },
            status=status.HTTP_202_ACCEPTED,
        )
'''

class BulkReindexMissingView(APIView):
    """
    POST  /api/v1/document-search/reindex-missing/
    – queues indexing for every file that currently has **no** VectorChunk rows.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        task = bulk_reindex.delay()
        return Response(
            {"message": "Bulk re-index started", "task_id": task.id},
            status=status.HTTP_202_ACCEPTED,
        )

'''
class ChunkedFileSearchView(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        query = request.data.get("query")
        file_id = request.data.get("file_id")
        top_k = int(request.data.get("top_k", 5))

        if not query:
            return Response({"error": "Missing 'query' in request"}, status=400)

        # Submit task
        task = exec_search.apply_async(args=[user.id, query, file_id, top_k])

        # Wait for result (max 60s)
        timeout = 60
        start = time.time()
        while not task.ready() and (time.time() - start) < timeout:
            time.sleep(1)

        if task.successful():
            return Response({
                "status": "ok",
                "query": query,
                "results": task.result,
                "count": len(task.result),
            })
        else:
            return Response({
                "status": "error",
                "detail": str(task.result) if task.result else "search-failed"
            }, status=500)
'''


class ChunkedFileSearchView(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        query = request.data.get("query")
        file_id = request.data.get("file_id")
        top_k = int(request.data.get("top_k", 5))

        if not query:
            return Response({"error": "Missing 'query' in request"}, status=400)

        # ✅ Check if the file is accessible
        if file_id:
            owns_file = File.objects.filter(id=file_id, uploaded_by=user).exists()
            shared_file = FileAccessEntry.objects.filter(file_id=file_id, user=user, can_read=True).exists()
            if not owns_file and not shared_file:
                return Response({"error": "You do not have permission to access this file."}, status=403)

        # 🚀 Submit task
        task = exec_search.apply_async(args=[user.id, query, file_id, top_k])

        # Wait for result (max 60s)
        timeout = 60
        start = time.time()
        while not task.ready() and (time.time() - start) < timeout:
            time.sleep(1)

        if task.successful():
            return Response({
                "status": "ok",
                "query": query,
                "results": task.result,
                "count": len(task.result),
            })
        else:
            return Response({
                "status": "error",
                "detail": str(task.result) if task.result else "search-failed"
            }, status=500)


class AdvancedDocumentSearchView(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        query = request.data.get("query")
        top_k = int(request.data.get("top_k", 10))
        filters = request.data.get("filters", {})

        if not query:
            return Response({"error": "Query is required"}, status=400)

        # Step 1: run vector search
        embed_model = _get_model()
        query_vector = embed_model.encode([query])[0]

        collection = _get_collection()
        results = collection.search(
            data=[query_vector],
            anns_field="vector",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=top_k,
            output_fields=["file_id", "chunk_text"],
        )

        vector_file_ids = list({hit.entity.get("file_id") for hit in results[0]})

        if not vector_file_ids:
            return Response({"count": 0, "results": []}, status=200)

        # Step 2: compute accessible files (owned or shared)
        accessible_file_ids = list(
            File.objects.filter(uploaded_by=user).values_list("id", flat=True)
        ) + list(
            FileAccessEntry.objects.filter(user=user, can_read=True).values_list("file_id", flat=True)
        )

        # Step 3: filter intersection of vector results and accessible files
        allowed_file_ids = set(vector_file_ids) & set(accessible_file_ids)

        if not allowed_file_ids:
            return Response({"count": 0, "results": []}, status=200)

        # Step 4: build full queryset with additional filters
        q = Q(id__in=allowed_file_ids)

        if filters.get("created_from"):
            q &= Q(created_at__gte=datetime.fromisoformat(filters["created_from"]))
        if filters.get("created_to"):
            q &= Q(created_at__lte=datetime.fromisoformat(filters["created_to"]))
        if filters.get("author"):
            q &= Q(metadata__author__icontains=filters["author"])
        if filters.get("project_id"):
            q &= Q(project_id=filters["project_id"])
        if filters.get("service_id"):
            q &= Q(service_id=filters["service_id"])

        files = File.objects.filter(q).prefetch_related("metadata")

        # Step 5: format results
        results_out = []
        for file in files:
            metadata = file.metadata.first()
            results_out.append({
                "file_id": file.id,
                "filename": file.filename,
                "file_size": file.file_size,
                "file_type": file.file_type,
                "created_at": file.created_at,
                "author": metadata.author if metadata else None,
                "keywords": metadata.keywords if metadata else None,
                "chunk_text": next(
                    (hit.entity.get("chunk_text") for hit in results[0] if hit.entity.get("file_id") == file.id),
                    ""
                ),
                "score": next(
                    (hit.score for hit in results[0] if hit.entity.get("file_id") == file.id),
                    None
                )
            })

        return Response({
            "count": len(results_out),
            "results": results_out
        }, status=200)


'''
class AdvancedDocumentSearchView(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        query = request.data.get("query")
        top_k = int(request.data.get("top_k", 10))
        filters = request.data.get("filters", {})

        if not query:
            return Response({"error": "Query is required"}, status=400)

        # Step 1: run vector search
        embed_model = _get_model()
        query_vector = embed_model.encode([query])[0]

        collection = _get_collection()
        results = collection.search(
            data=[query_vector],
            anns_field="vector",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=top_k,
            output_fields=["file_id", "chunk_text"],
        )

        file_ids = list({hit.entity.get("file_id") for hit in results[0]})

        # Step 2: build Postgres filters
        q = Q(user=user)

        if filters.get("created_from"):
            q &= Q(created_at__gte=datetime.fromisoformat(filters["created_from"]))
        if filters.get("created_to"):
            q &= Q(created_at__lte=datetime.fromisoformat(filters["created_to"]))
        if filters.get("author"):
            q &= Q(metadata__author__icontains=filters["author"])
        if filters.get("project_id"):
            q &= Q(project_id=filters["project_id"])
        if filters.get("service_id"):
            q &= Q(service_id=filters["service_id"])

        # Apply file_id constraint if we have vector hits
        if file_ids:
            q &= Q(id__in=file_ids)
        else:
            return Response({"count": 0, "results": []}, status=200)

        files = File.objects.filter(q).prefetch_related("metadata")

        results_out = []
        for file in files:
            metadata = file.metadata.first()
            results_out.append({
                "file_id": file.id,
                "filename": file.filename,
                "file_size": file.file_size,
                "file_type": file.file_type,
                "created_at": file.created_at,
                "author": metadata.author if metadata else None,
                "keywords": metadata.keywords if metadata else None,
                "chunk_text": next(
                    (hit.entity.get("chunk_text") for hit in results[0] if hit.entity.get("file_id") == file.id),
                    ""
                ),
                "score": next(
                    (hit.score for hit in results[0] if hit.entity.get("file_id") == file.id),
                    None
                )
            })

        return Response({
            "count": len(results_out),
            "results": results_out
        }, status=200)
'''


class SearchResultView(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id, *args, **kwargs):
        task_id = str(task_id)                         # ← ADD THIS
        result = AsyncResult(task_id)

        if result.state == "PENDING":
            return Response({"status": "pending"}, status=202)

        elif result.state == "FAILURE":
            return Response({
                "status": "error",
                "error": str(result.result),
            }, status=500)

        elif result.state == "SUCCESS":
            return Response({
                "status": "ok",
                "results": result.result,
                "count": len(result.result) if result.result else 0,
            })

        else:
            return Response({"status": result.state})

