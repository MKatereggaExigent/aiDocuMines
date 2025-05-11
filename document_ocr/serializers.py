from rest_framework import serializers
from core.models import File
from .models import OCRRun, OCRFile, OCRStorage


class OCRRunSerializer(serializers.ModelSerializer):
    """Serializer for OCR processing runs."""

    class Meta:
        model = OCRRun
        fields = [
            "id",
            "project_id",
            "service_id",
            "client_name",
            "status",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OCRFileSerializer(serializers.ModelSerializer):
    """Serializer for files processed via OCR."""

    original_file = serializers.PrimaryKeyRelatedField(queryset=File.objects.all())  # ✅ Link to the original file

    class Meta:
        model = OCRFile
        fields = [
            "id",
            "run",
            "original_file",
            "ocr_filepath",
            "docx_path",
            "raw_docx_path",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OCRStorageSerializer(serializers.ModelSerializer):
    """Serializer for storage locations of OCR-processed files."""

    class Meta:
        model = OCRStorage
        fields = [
            "storage_id",
            "run",
            "upload_storage_location",
            "ocr_storage_location",
        ]
        read_only_fields = ["storage_id"]
