from rest_framework import serializers
from document_automation.models import AutomationTemplate, AutomationRun, AutomationResult, ClauseCategory, Clause, TemplateField


class AutomationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationTemplate
        fields = [
            "id",
            "name",
            "description",
            "file",
            "template_type",
            "project_id",
            "service_id",
            "client_name",
            "created_at",
            "updated_at",
        ]


class AutomationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationRun
        fields = [
            "id",
            "project_id",
            "service_id",
            "client_name",
            "template",
            "input_data",
            "status",
            "created_at",
            "updated_at",
            "error_message",
            "bulk_count",
            "bulk_data",
            "clause_ids",
            "output_format",
        ]


class AutomationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationResult
        fields = [
            "id",
            "run",
            "output_filepath",
            "pdf_output_path",
            "output_filename",
            "variables_used",
            "generation_index",
            "status",
            "created_at",
            "updated_at",
        ]


class ClauseCategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = ClauseCategory
        fields = [
            "id",
            "name",
            "description",
            "parent",
            "children",
            "project_id",
            "client_name",
            "created_at",
            "updated_at",
        ]

    def get_children(self, obj):
        return ClauseCategorySerializer(obj.children.all(), many=True).data


class ClauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clause
        fields = [
            "id",
            "category",
            "title",
            "content",
            "version",
            "is_active",
            "project_id",
            "service_id",
            "client_name",
            "variables",
            "created_at",
            "updated_at",
        ]


class TemplateFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateField
        fields = [
            "id",
            "template",
            "name",
            "field_type",
            "required",
            "default_value",
            "description",
            "options",
            "order",
            "created_at",
            "updated_at",
        ]
