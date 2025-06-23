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

import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# 🧠  Connect to Milvus collection
# ─────────────────────────────────────────────────────────────
def _get_collection() -> Collection:
    connections.connect(alias="default", host="localhost", port="19530")
    collection = Collection("vector_chunks")  # must match tasks.py
    collection.load()
    return collection


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
    """
    POST /api/v1/document-search/search/
    {
        "query":  "...",
        "top_k":  8,
        "file_id": 123   # optional
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = SearchRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user      = request.user
        query     = ser.validated_data["query"]
        file_id   = ser.validated_data.get("file_id")
        top_k     = ser.validated_data["top_k"]

        cache_key = f"search:{user.id}:{file_id}:{top_k}:{hash(query)}"
        cached    = cache.get(cache_key)
        if cached:                                     # ⚡ 0-ms hit
            return Response(SearchResultSerializer(cached, many=True).data)

        # off-load to Celery, wait ≤ 5 s (fast in-RAM Milvus call)
        async_res: AsyncResult = exec_search.apply_async(
            args=[user.id, query, file_id, top_k]
        )
        try:
            hits = async_res.get(timeout=5)            # quick path
            return Response(SearchResultSerializer(hits, many=True).data)
        except Exception:
            # still running – tell client to poll later
            return Response(
                AsyncSearchResponse({"task_id": async_res.id}).data,
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

