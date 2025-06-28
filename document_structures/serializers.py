# document_structures/serializers.py

from rest_framework import serializers
from document_structures import models
from core.models import File, Run
from django.contrib.auth import get_user_model

User = get_user_model()


# ----------------------------
# Simple Related Serializers
# ----------------------------

class UserMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class FileMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ["id", "filename", "filepath", "file_size", "file_type"]


class RunMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Run
        fields = ["run_id", "status", "created_at"]


# ------------------------------------
# Document Structure Run Serializers
# ------------------------------------

class DocumentStructureRunSerializer(serializers.ModelSerializer):
    file = FileMinimalSerializer(read_only=True)
    user = UserMinimalSerializer(read_only=True)
    run = RunMinimalSerializer(read_only=True)

    class Meta:
        model = models.DocumentStructureRun
        fields = [
            "id",
            "run",
            "file",
            "user",
            "partition_strategy",
            "status",
            "error_message",
            "created_at",
            "updated_at",
        ]


# ---------------------------------------
# Document Element Serializers
# ---------------------------------------

class DocumentElementSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=models.DocumentElement.objects.all(),
        allow_null=True,
        required=False
    )

    class Meta:
        model = models.DocumentElement
        fields = [
            "id",
            "run",
            "element_type",
            "text",
            "metadata",
            "parent",
            "page_number",
            "coordinates",
            "order",
            "embedding",
            "languages",
            "list_level",
            "list_item",
            "created_at",
            "updated_at",
        ]


class DocumentElementDetailSerializer(DocumentElementSerializer):
    """
    For detailed retrieval, include children elements in nested format if desired.
    """
    children = serializers.SerializerMethodField()

    def get_children(self, obj):
        children_qs = obj.children.all().order_by("order")
        return DocumentElementSerializer(children_qs, many=True).data

    class Meta(DocumentElementSerializer.Meta):
        fields = DocumentElementSerializer.Meta.fields + ["children"]


# ---------------------------------------
# Document Table and Cell Serializers
# ---------------------------------------

class DocumentTableCellSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DocumentTableCell
        fields = [
            "id",
            "table",
            "row_idx",
            "col_idx",
            "text",
            "rowspan",
            "colspan",
            "created_at",
            "updated_at",
        ]


class DocumentTableSerializer(serializers.ModelSerializer):
    cells = DocumentTableCellSerializer(many=True, read_only=True)

    class Meta:
        model = models.DocumentTable
        fields = [
            "id",
            "run",
            "page_number",
            "order",
            "html",
            "csv",
            "json",
            "cells",
            "created_at",
            "updated_at",
        ]


# ---------------------------------------
# Document Comparison Serializers
# ---------------------------------------

class DocumentComparisonSerializer(serializers.ModelSerializer):
    run_1 = DocumentStructureRunSerializer(read_only=True)
    run_2 = DocumentStructureRunSerializer(read_only=True)

    class Meta:
        model = models.DocumentComparison
        fields = [
            "id",
            "run_1",
            "run_2",
            "lexical_similarity",
            "semantic_similarity",
            "deviation_report",
            "status",
            "created_at",
            "updated_at",
        ]


# ---------------------------------------
# Section Edits Serializers
# ---------------------------------------

class SectionEditSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)

    class Meta:
        model = models.SectionEdit
        fields = [
            "id",
            "element",
            "user",
            "original_text",
            "edited_text",
            "created_at",
            "updated_at",
        ]


# -----------------------------
# Bulk serializers if needed
# -----------------------------

class DocumentElementBulkCreateSerializer(serializers.ListSerializer):
    """
    Enables bulk create of elements in one request.
    """

    def create(self, validated_data):
        elements = [models.DocumentElement(**item) for item in validated_data]
        return models.DocumentElement.objects.bulk_create(elements)


class DocumentElementWriteSerializer(serializers.ModelSerializer):
    """
    For creating or updating elements individually or in bulk.
    """

    class Meta:
        model = models.DocumentElement
        list_serializer_class = DocumentElementBulkCreateSerializer
        fields = [
            "run",
            "element_type",
            "text",
            "metadata",
            "parent",
            "page_number",
            "coordinates",
            "order",
            "embedding",
            "languages",
            "list_level",
            "list_item",
        ]

