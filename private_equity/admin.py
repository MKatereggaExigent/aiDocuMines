from django.contrib import admin
from .models import (
    DueDiligenceRun, DocumentClassification, RiskClause, 
    FindingsReport, DataRoomConnector
)


@admin.register(DueDiligenceRun)
class DueDiligenceRunAdmin(admin.ModelAdmin):
    list_display = ('deal_name', 'target_company', 'deal_type', 'data_room_source', 'created_at')
    list_filter = ('deal_type', 'data_room_source', 'created_at')
    search_fields = ('deal_name', 'target_company')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Deal Information', {
            'fields': ('run', 'deal_name', 'target_company', 'deal_type', 'deal_value', 'expected_close_date')
        }),
        ('Data Room', {
            'fields': ('data_room_source',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DocumentClassification)
class DocumentClassificationAdmin(admin.ModelAdmin):
    list_display = ('file', 'document_type', 'confidence_score', 'is_verified', 'created_at')
    list_filter = ('document_type', 'is_verified', 'created_at')
    search_fields = ('file__filename', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Classification', {
            'fields': ('file', 'user', 'due_diligence_run', 'document_type', 'confidence_score')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verified_by')
        }),
        ('Metadata', {
            'fields': ('classification_metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RiskClause)
class RiskClauseAdmin(admin.ModelAdmin):
    list_display = ('file', 'clause_type', 'risk_level', 'page_number', 'is_reviewed', 'created_at')
    list_filter = ('clause_type', 'risk_level', 'is_reviewed', 'created_at')
    search_fields = ('file__filename', 'clause_text', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Clause Information', {
            'fields': ('file', 'user', 'due_diligence_run', 'clause_type', 'clause_text')
        }),
        ('Risk Assessment', {
            'fields': ('risk_level', 'risk_explanation', 'mitigation_suggestions')
        }),
        ('Location', {
            'fields': ('page_number', 'position_start', 'position_end')
        }),
        ('Review Status', {
            'fields': ('is_reviewed', 'reviewed_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FindingsReport)
class FindingsReportAdmin(admin.ModelAdmin):
    list_display = ('report_name', 'due_diligence_run', 'status', 'total_documents_reviewed', 'high_risk_items_count', 'generated_at')
    list_filter = ('status', 'generated_at')
    search_fields = ('report_name', 'due_diligence_run__deal_name', 'user__email')
    readonly_fields = ('generated_at', 'updated_at')
    
    fieldsets = (
        ('Report Information', {
            'fields': ('due_diligence_run', 'user', 'report_name', 'status')
        }),
        ('Summary', {
            'fields': ('executive_summary', 'total_documents_reviewed', 'total_risk_clauses_found', 'high_risk_items_count')
        }),
        ('Structured Data', {
            'fields': ('document_summary', 'risk_summary', 'key_findings', 'recommendations'),
            'classes': ('collapse',)
        }),
        ('Finalization', {
            'fields': ('finalized_at', 'finalized_by')
        }),
        ('Timestamps', {
            'fields': ('generated_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DataRoomConnector)
class DataRoomConnectorAdmin(admin.ModelAdmin):
    list_display = ('connector_name', 'connector_type', 'due_diligence_run', 'sync_status', 'last_sync_at', 'is_active')
    list_filter = ('connector_type', 'sync_status', 'is_active', 'created_at')
    search_fields = ('connector_name', 'due_diligence_run__deal_name', 'user__email')
    readonly_fields = ('last_sync_at', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Connector Information', {
            'fields': ('user', 'due_diligence_run', 'connector_type', 'connector_name', 'is_active')
        }),
        ('Sync Status', {
            'fields': ('sync_status', 'last_sync_at', 'sync_error_message')
        }),
        ('Configuration', {
            'fields': ('connection_config',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
