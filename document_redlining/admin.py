from django.contrib import admin
from document_redlining.models import RedliningRun, RedliningResult


@admin.register(RedliningRun)
class RedliningRunAdmin(admin.ModelAdmin):
    list_display = ("id", "client_name", "status", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("id", "client_name", "project_id", "service_id")


@admin.register(RedliningResult)
class RedliningResultAdmin(admin.ModelAdmin):
    list_display = ("id", "run", "original_file", "comparison_file", "status", "author", "comparison_date", "created_at")
    list_filter = ("status",)
    search_fields = ("id", "author")
    readonly_fields = ("comparison_date", "created_at", "updated_at")
    fieldsets = (
        (None, {
            "fields": ("run", "original_file", "comparison_file", "status", "author"),
        }),
        ("Outputs", {
            "fields": ("diff_output_path", "diff_html", "redline_docx_path", "redline_pdf_path"),
        }),
        ("Statistics", {
            "fields": ("comparison_stats",),
        }),
        ("Timestamps", {
            "fields": ("comparison_date", "created_at", "updated_at"),
        }),
    )
