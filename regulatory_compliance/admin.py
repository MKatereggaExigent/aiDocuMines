from django.contrib import admin
from .models import (
    ComplianceRun, RegulatoryRequirement, PolicyMapping, DSARRequest,
    DataInventory, RedactionTask, ComplianceAlert
)


@admin.register(ComplianceRun)
class ComplianceRunAdmin(admin.ModelAdmin):
    list_display = ('organization_name', 'compliance_framework', 'assessment_start_date', 'assessment_end_date', 'created_at')
    list_filter = ('compliance_framework', 'created_at', 'assessment_start_date')
    search_fields = ('organization_name', 'compliance_officer', 'legal_counsel')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Organization Information', {
            'fields': ('run', 'organization_name', 'compliance_framework', 'assessment_scope')
        }),
        ('Regulatory Context', {
            'fields': ('applicable_regulations', 'jurisdiction')
        }),
        ('Assessment Period', {
            'fields': ('assessment_start_date', 'assessment_end_date')
        }),
        ('Key Stakeholders', {
            'fields': ('compliance_officer', 'legal_counsel')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RegulatoryRequirement)
class RegulatoryRequirementAdmin(admin.ModelAdmin):
    list_display = ('requirement_id', 'requirement_title', 'category', 'compliance_status', 'risk_level', 'due_date')
    list_filter = ('category', 'compliance_status', 'risk_level', 'due_date', 'created_at')
    search_fields = ('requirement_id', 'requirement_title', 'requirement_text')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Requirement Information', {
            'fields': ('user', 'compliance_run', 'requirement_id', 'requirement_title')
        }),
        ('Requirement Content', {
            'fields': ('requirement_text', 'category')
        }),
        ('Compliance Status', {
            'fields': ('compliance_status', 'risk_level')
        }),
        ('Implementation Details', {
            'fields': ('implementation_notes', 'remediation_plan', 'responsible_party')
        }),
        ('Important Dates', {
            'fields': ('due_date', 'last_reviewed', 'next_review')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PolicyMapping)
class PolicyMappingAdmin(admin.ModelAdmin):
    list_display = ('policy_name', 'regulatory_requirement', 'mapping_strength', 'mapping_confidence', 'created_at')
    list_filter = ('mapping_strength', 'created_at')
    search_fields = ('policy_name', 'policy_section', 'gap_analysis')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Mapping Information', {
            'fields': ('user', 'compliance_run', 'regulatory_requirement', 'policy_document')
        }),
        ('Policy Details', {
            'fields': ('policy_name', 'policy_section')
        }),
        ('Mapping Analysis', {
            'fields': ('mapping_strength', 'mapping_confidence')
        }),
        ('Gap Analysis', {
            'fields': ('gap_analysis', 'recommendations')
        }),
        ('Metadata', {
            'fields': ('mapping_metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DSARRequest)
class DSARRequestAdmin(admin.ModelAdmin):
    list_display = ('request_id', 'data_subject_name', 'request_type', 'status', 'request_date', 'response_due_date')
    list_filter = ('request_type', 'status', 'verification_status', 'request_date', 'response_due_date')
    search_fields = ('request_id', 'data_subject_name', 'data_subject_email', 'request_description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Request Information', {
            'fields': ('user', 'compliance_run', 'request_id', 'request_type')
        }),
        ('Data Subject Information', {
            'fields': ('data_subject_name', 'data_subject_email', 'data_subject_id')
        }),
        ('Request Details', {
            'fields': ('request_date', 'request_description', 'verification_status')
        }),
        ('Processing Status', {
            'fields': ('status', 'response_due_date', 'response_date', 'response_method')
        }),
        ('Data Collection Results', {
            'fields': ('data_sources_searched', 'personal_data_found', 'data_categories')
        }),
        ('Processing Notes', {
            'fields': ('processing_notes', 'rejection_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DataInventory)
class DataInventoryAdmin(admin.ModelAdmin):
    list_display = ('activity_name', 'legal_basis', 'international_transfers', 'dpia_required', 'dpia_completed', 'created_at')
    list_filter = ('legal_basis', 'international_transfers', 'dpia_required', 'dpia_completed', 'created_at')
    search_fields = ('activity_name', 'activity_description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Activity Information', {
            'fields': ('user', 'compliance_run', 'activity_name', 'activity_description')
        }),
        ('Data Categories', {
            'fields': ('data_categories', 'special_categories', 'data_subject_categories')
        }),
        ('Legal Basis and Purposes', {
            'fields': ('legal_basis', 'processing_purposes')
        }),
        ('Data Flow', {
            'fields': ('data_sources', 'data_recipients')
        }),
        ('International Transfers', {
            'fields': ('international_transfers', 'transfer_countries', 'transfer_safeguards')
        }),
        ('Retention', {
            'fields': ('retention_period', 'retention_criteria')
        }),
        ('Security Measures', {
            'fields': ('technical_measures', 'organizational_measures')
        }),
        ('Data Protection Impact Assessment', {
            'fields': ('dpia_required', 'dpia_completed', 'dpia_document')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RedactionTask)
class RedactionTaskAdmin(admin.ModelAdmin):
    list_display = ('task_name', 'redaction_type', 'status', 'redaction_count', 'qa_required', 'qa_completed', 'created_at')
    list_filter = ('redaction_type', 'status', 'qa_required', 'qa_completed', 'created_at')
    search_fields = ('task_name', 'source_document__filename')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Task Information', {
            'fields': ('user', 'compliance_run', 'task_name', 'source_document')
        }),
        ('Redaction Parameters', {
            'fields': ('redaction_type', 'redaction_rules', 'redaction_patterns')
        }),
        ('Processing Status', {
            'fields': ('status', 'redacted_document')
        }),
        ('Results', {
            'fields': ('redaction_count', 'redaction_summary')
        }),
        ('Quality Assurance', {
            'fields': ('qa_required', 'qa_completed', 'qa_reviewer', 'qa_notes')
        }),
        ('Processing Metadata', {
            'fields': ('processing_metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ComplianceAlert)
class ComplianceAlertAdmin(admin.ModelAdmin):
    list_display = ('alert_title', 'alert_type', 'severity', 'priority', 'status', 'assigned_to', 'due_date', 'created_at')
    list_filter = ('alert_type', 'severity', 'priority', 'status', 'due_date', 'created_at')
    search_fields = ('alert_title', 'alert_description', 'assigned_to')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('related_documents',)
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('user', 'compliance_run', 'alert_type', 'alert_title', 'alert_description')
        }),
        ('Severity and Priority', {
            'fields': ('severity', 'priority')
        }),
        ('Related Objects', {
            'fields': ('related_requirement', 'related_dsar', 'related_documents')
        }),
        ('Alert Status', {
            'fields': ('status', 'assigned_to', 'due_date')
        }),
        ('Resolution Details', {
            'fields': ('resolution_notes', 'resolved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
