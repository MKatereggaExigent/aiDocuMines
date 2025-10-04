from django.contrib import admin
from .models import (
    MassClaimsRun, IntakeForm, EvidenceDocument, PIIRedaction,
    ExhibitPackage, SettlementTracking, ClaimantCommunication
)


@admin.register(MassClaimsRun)
class MassClaimsRunAdmin(admin.ModelAdmin):
    list_display = ('case_name', 'case_number', 'case_type', 'status', 'claim_deadline', 'created_at')
    list_filter = ('case_type', 'status', 'created_at')
    search_fields = ('case_name', 'case_number', 'court_jurisdiction')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Case Information', {
            'fields': ('run', 'case_name', 'case_number', 'court_jurisdiction', 'case_type')
        }),
        ('Timeline', {
            'fields': ('claim_deadline', 'settlement_amount')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(IntakeForm)
class IntakeFormAdmin(admin.ModelAdmin):
    list_display = ('claimant_id', 'mass_claims_run', 'processing_status', 'is_duplicate', 'is_valid', 'submitted_at')
    list_filter = ('processing_status', 'is_duplicate', 'is_valid', 'submitted_at')
    search_fields = ('claimant_id', 'user__email')
    readonly_fields = ('claimant_id', 'submitted_at', 'processed_at')
    
    fieldsets = (
        ('Claimant Information', {
            'fields': ('user', 'mass_claims_run', 'claimant_id', 'claimant_data')
        }),
        ('Processing Status', {
            'fields': ('processing_status', 'processed_at', 'processed_by')
        }),
        ('Validation', {
            'fields': ('is_valid', 'validation_errors')
        }),
        ('Duplicate Detection', {
            'fields': ('is_duplicate', 'duplicate_of', 'duplicate_score')
        }),
        ('Timestamps', {
            'fields': ('submitted_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(EvidenceDocument)
class EvidenceDocumentAdmin(admin.ModelAdmin):
    list_display = ('file', 'evidence_type', 'relevance_score', 'is_culled', 'contains_pii', 'privilege_status', 'created_at')
    list_filter = ('evidence_type', 'is_culled', 'contains_pii', 'privilege_status', 'created_at')
    search_fields = ('file__filename', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Document Information', {
            'fields': ('file', 'user', 'mass_claims_run', 'evidence_type')
        }),
        ('Culling and Relevance', {
            'fields': ('is_culled', 'cull_reason', 'relevance_score')
        }),
        ('Content Analysis', {
            'fields': ('contains_pii', 'privilege_status')
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


@admin.register(PIIRedaction)
class PIIRedactionAdmin(admin.ModelAdmin):
    list_display = ('file', 'pii_type', 'page_number', 'confidence_score', 'is_verified', 'created_at')
    list_filter = ('pii_type', 'is_verified', 'created_at')
    search_fields = ('file__filename', 'original_text', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('PII Information', {
            'fields': ('file', 'user', 'mass_claims_run', 'pii_type')
        }),
        ('Content', {
            'fields': ('original_text', 'redacted_text')
        }),
        ('Location', {
            'fields': ('page_number', 'position_start', 'position_end')
        }),
        ('Verification', {
            'fields': ('confidence_score', 'is_verified', 'verified_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ExhibitPackage)
class ExhibitPackageAdmin(admin.ModelAdmin):
    list_display = ('package_name', 'mass_claims_run', 'bates_start', 'bates_end', 'total_pages', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('package_name', 'bates_start', 'bates_end', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'produced_at')
    filter_horizontal = ('files',)
    
    fieldsets = (
        ('Package Information', {
            'fields': ('user', 'mass_claims_run', 'package_name', 'description')
        }),
        ('Files', {
            'fields': ('files',)
        }),
        ('Bates Numbering', {
            'fields': ('bates_prefix', 'bates_start', 'bates_end', 'total_pages')
        }),
        ('Status', {
            'fields': ('status', 'produced_at')
        }),
        ('Production Metadata', {
            'fields': ('production_metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SettlementTracking)
class SettlementTrackingAdmin(admin.ModelAdmin):
    list_display = ('mass_claims_run', 'settlement_type', 'total_settlement_amount', 'total_approved_claims', 'status', 'created_at')
    list_filter = ('settlement_type', 'notice_type', 'status', 'created_at')
    search_fields = ('mass_claims_run__case_name', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Settlement Information', {
            'fields': ('mass_claims_run', 'user', 'settlement_type')
        }),
        ('Financial Details', {
            'fields': ('total_settlement_amount', 'attorney_fees', 'administration_costs', 'net_settlement_fund')
        }),
        ('Notice Information', {
            'fields': ('notice_type', 'notice_deadline', 'objection_deadline', 'opt_out_deadline')
        }),
        ('Distribution Tracking', {
            'fields': ('total_eligible_claimants', 'total_approved_claims', 'total_distributed_amount')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ClaimantCommunication)
class ClaimantCommunicationAdmin(admin.ModelAdmin):
    list_display = ('intake_form', 'communication_type', 'subject', 'sent_at', 'delivered_at', 'requires_follow_up')
    list_filter = ('communication_type', 'requires_follow_up', 'sent_at')
    search_fields = ('subject', 'message_content', 'intake_form__claimant_id', 'user__email')
    readonly_fields = ('sent_at', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Communication Information', {
            'fields': ('user', 'mass_claims_run', 'intake_form', 'communication_type')
        }),
        ('Message Content', {
            'fields': ('subject', 'message_content')
        }),
        ('Delivery Tracking', {
            'fields': ('sent_at', 'delivered_at', 'read_at', 'responded_at')
        }),
        ('Response', {
            'fields': ('response_content', 'requires_follow_up')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
