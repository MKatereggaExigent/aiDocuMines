from rest_framework import serializers
from core.models import File
from .models import OCRRun, OCRFile, OCRStorage, OCRBatch


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
            "ocr_option",  # Added ocr_option to track the type of OCR run (Basic or Advanced)
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OCRFileSerializer(serializers.ModelSerializer):
    """Serializer for files processed via OCR."""

    original_file = serializers.PrimaryKeyRelatedField(queryset=File.objects.all())  # Link to the original file
    ocr_option = serializers.CharField(max_length=20)  # Added ocr_option to store the OCR option applied

    class Meta:
        model = OCRFile
        fields = [
            "id",
            "run",
            "original_file",
            "ocr_filepath",
            "docx_path",
            "raw_docx_path",
            "ocr_option",  # Added ocr_option to track the OCR type applied to the file
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


class OCRBatchSerializer(serializers.ModelSerializer):
    """Serializer for OCR batches (for PDFs that have been split into smaller chunks)."""

    ocr_file = serializers.PrimaryKeyRelatedField(queryset=OCRFile.objects.all())  # Link to the OCR file processed in the batch

    class Meta:
        model = OCRBatch
        fields = [
            "id",
            "ocr_file",
            "batch_filepath",
            "batch_status",
            "start_page",
            "end_page",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

