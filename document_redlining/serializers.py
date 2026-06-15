from rest_framework import serializers
from document_redlining.models import RedliningRun, RedliningResult


class RedliningRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = RedliningRun
        fields = [
            "id",
            "project_id",
            "service_id",
            "client_name",
            "status",
            "created_at",
            "updated_at",
            "error_message",
        ]


class RedliningResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = RedliningResult
        fields = [
            "id",
            "run",
            "original_file",
            "comparison_file",
            "diff_output_path",
            "diff_html",
            "redline_docx_path",
            "redline_pdf_path",
            "comparison_stats",
            "author",
            "comparison_date",
            "status",
            "created_at",
            "updated_at",
        ]
