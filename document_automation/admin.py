from django.contrib import admin
from document_automation.models import AutomationTemplate, AutomationRun, AutomationResult, ClauseCategory, Clause, TemplateField


@admin.register(AutomationTemplate)
class AutomationTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "template_type", "project_id", "service_id", "created_at")
    search_fields = ("name", "project_id", "service_id")
    list_filter = ("template_type",)


@admin.register(AutomationRun)
class AutomationRunAdmin(admin.ModelAdmin):
    list_display = ("id", "template", "status", "client_name", "bulk_count", "output_format", "created_at")
    search_fields = ("id", "client_name", "project_id")
    list_filter = ("status", "output_format")


@admin.register(AutomationResult)
class AutomationResultAdmin(admin.ModelAdmin):
    list_display = ("id", "run", "status", "generation_index", "output_filename", "created_at")
    search_fields = ("id",)
    list_filter = ("status",)


@admin.register(ClauseCategory)
class ClauseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "project_id", "client_name", "created_at")
    search_fields = ("name", "project_id")
    list_filter = ("project_id",)


@admin.register(Clause)
class ClauseAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "version", "is_active", "project_id", "service_id", "created_at")
    search_fields = ("title", "project_id", "service_id")
    list_filter = ("is_active", "category")


@admin.register(TemplateField)
class TemplateFieldAdmin(admin.ModelAdmin):
    list_display = ("name", "template", "field_type", "required", "order", "created_at")
    search_fields = ("name", "template__name")
    list_filter = ("field_type", "required")
