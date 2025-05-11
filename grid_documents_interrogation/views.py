from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Topic, Query
from .serializers import TopicSerializer, QuerySerializer
from core.models import File
from custom_authentication.models import CustomUser

from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from .tasks import process_file_query, process_db_query

import csv
from io import StringIO
import os

import pandas as pd

from .db_query_tools import fetch_column_names, generate_sql_query, execute_sql_query
from .file_readers import read_pdf_file

class TopicViewSet(viewsets.ModelViewSet):
    serializer_class = TopicSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Topic.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        topic = self.get_object()
        files = topic.files.all()

        summary = {
            "id": topic.id,
            "project_id": topic.project_id,
            "service_id": topic.service_id,
            "chat_date": topic.chat_date.isoformat(),
            "files": [
                {
                    "file_id": f.id,
                    "file_name": f.filename,
                    "data_source": "File",
                    "created_at": f.created_at.isoformat(),
                    "status": f.status,
                }
                for f in files
            ]
        }
        return Response(summary)

    @action(detail=True, methods=['get'])
    def active_file(self, request, pk=None):
        topic = self.get_object()
        latest_file = topic.files.order_by('-created_at').first()
        if latest_file:
            return Response({
                "file_id": latest_file.id,
                "file_name": latest_file.filename
            })
        return Response({"active_file": None})

    @action(detail=False, methods=['post'], url_path='start-interrogation')
    def start_interrogation(self, request):
        project_id = request.data.get("project_id")
        service_id = request.data.get("service_id")
        name = request.data.get("name", f"{project_id}-{service_id}")

        if not project_id or not service_id:
            return Response({"error": "project_id and service_id are required"}, status=400)

        topic, created = Topic.objects.get_or_create(
            user=request.user,
            project_id=project_id,
            service_id=service_id,
            defaults={"name": name}
        )

        return Response({
            "topic_id": topic.id,
            "project_id": topic.project_id,
            "service_id": topic.service_id,
            "created": created
        }, status=200)


class QueryViewSet(viewsets.ModelViewSet):
    serializer_class = QuerySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Query.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='ask')
    def ask_query(self, request):
        topic_id = request.data.get("topic_id")
        query_text = request.data.get("query_text")
        data_source = request.data.get("data_source", "file")
        file_id = request.data.get("file_id")

        llm_config = request.data.get("llm_config", {
            "provider": "openai",
            "model": "gpt-4o"
        })

        if not topic_id or not query_text:
            return Response({"error": "topic_id and query_text are required."}, status=400)

        topic = get_object_or_404(Topic, id=topic_id, user=request.user)

        try:
            if data_source == "file":
                if not file_id:
                    return Response({"error": "file_id is required for file-based queries."}, status=400)

                file = get_object_or_404(File, id=file_id)
                task = process_file_query.delay(query_text, file.filepath, llm_config)
            elif data_source == "db":
                connection_string = request.data.get("connection_string")
                table_name = request.data.get("table")
                task = process_db_query.delay(query_text, connection_string, table_name, llm_config)
                file = None
            else:
                return Response({"error": "Invalid data_source. Must be 'file' or 'db'."}, status=400)

            result = task.get(timeout=60)

            query = Query.objects.create(
                topic=topic,
                user=request.user,
                file=file,
                query_text=query_text,
                response_text=result
            )

            return Response(QuerySerializer(query).data, status=201)

        except Exception as e:
            return Response({"error": f"Query processing failed: {str(e)}"}, status=500)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        query = self.get_object()
        queries = Query.objects.filter(topic=query.topic, user=request.user)

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Filename', 'Query', 'Response', 'Project', 'Service'])

        for q in queries:
            writer.writerow([
                q.file.filename if q.file else '',
                q.query_text,
                q.response_text,
                q.topic.project_id,
                q.topic.service_id
            ])

        output.seek(0)
        response = Response(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="chat_{pk}.csv"'
        return response

    @action(detail=True, methods=['delete'])
    def delete_chat(self, request, pk=None):
        query = self.get_object()
        file = query.file
        file_path = file.filepath if file else None

        query.delete()

        if file and not Query.objects.filter(file=file).exists():
            file.delete()
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

        return Response({"success": "Query and associated file deleted."})

    @action(detail=False, methods=['get'], url_path='fetch-previous')
    def fetch_previous_chat(self, request):
        topic_id = request.query_params.get("topic_id")
        query_id = request.query_params.get("query_id")

        if not topic_id or not query_id:
            return Response({"error": "Missing topic_id or query_id"}, status=400)

        query = get_object_or_404(
            Query,
            id=query_id,
            topic_id=topic_id,
            user=request.user
        )

        return Response({
            "query_text": query.query_text,
            "response_text": query.response_text
        }, status=200)

    @action(detail=False, methods=['get'], url_path='recent')
    def recent_queries(self, request):
        queries = Query.objects.filter(user=request.user).order_by('-created_at')[:10]
        return Response(QuerySerializer(queries, many=True).data)

    @action(detail=True, methods=['post'], url_path='reask')
    def reask_query(self, request, pk=None):
        original = get_object_or_404(Query, id=pk, user=request.user)
        new_query_text = request.data.get("query_text", original.query_text)
        llm_config = request.data.get("llm_config", {
            "provider": "openai",
            "model": "gpt-4o"
        })

        if original.file:
            task = process_file_query.delay(new_query_text, original.file.filepath, llm_config)
            result = task.get(timeout=60)
        else:
            return Response({"error": "Re-ask is only supported for file-based queries for now."}, status=400)

        new_query = Query.objects.create(
            topic=original.topic,
            user=request.user,
            file=original.file,
            query_text=new_query_text,
            response_text=result
        )

        return Response(QuerySerializer(new_query).data)

    @action(detail=False, methods=['get'], url_path='ocr-preview')
    def ocr_preview(self, request):
        file_id = request.query_params.get("file_id")
        if not file_id:
            return Response({"error": "file_id is required"}, status=400)

        file = get_object_or_404(File, id=file_id)
        try:
            text = read_pdf_file(file.filepath)
            return Response({"ocr_text": text[:5000]})
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @action(detail=False, methods=['post'], url_path='db-inspect')
    def db_inspect(self, request):
        connection_string = request.data.get("connection_string")
        table_name = request.data.get("table")

        try:
            cols = fetch_column_names(connection_string, table_name)
            sql = generate_sql_query(table_name, "overview", cols)
            df = execute_sql_query(connection_string, sql)

            sample_data = df.head().to_dict(orient="records") if hasattr(df, 'head') else str(df)
            return Response({
                "columns": cols,
                "sample_data": sample_data
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)

