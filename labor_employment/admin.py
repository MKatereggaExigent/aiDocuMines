from django.contrib import admin
from .models import (
    WorkplaceCommunicationsRun, CommunicationMessage, WageHourAnalysis,
    PolicyComparison, EEOCPacket, CommunicationPattern, ComplianceAlert
)


@admin.register(WorkplaceCommunicationsRun)
class WorkplaceCommunicationsRunAdmin(admin.ModelAdmin):
    list_display = ('case_name', 'company_name', 'case_type', 'analysis_start_date', 'analysis_end_date', 'created_at')
    list_filter = ('case_type', 'created_at')
    search_fields = ('case_name', 'company_name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Case Information', {
            'fields': ('run', 'case_name', 'company_name', 'case_type')
        }),
        ('Data Sources', {
            'fields': ('data_sources',)
        }),
        ('Analysis Period', {
            'fields': ('analysis_start_date', 'analysis_end_date')
        }),
        ('Key Personnel', {
            'fields': ('key_personnel',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CommunicationMessage)
class CommunicationMessageAdmin(admin.ModelAdmin):
    list_display = ('message_id', 'sender', 'message_type', 'sent_datetime', 'sentiment_score', 'toxicity_score', 'is_flagged')
    list_filter = ('message_type', 'is_flagged', 'is_privileged', 'contains_pii', 'sent_datetime')
    search_fields = ('message_id', 'sender', 'subject', 'content')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Message Information', {
            'fields': ('file', 'user', 'communications_run', 'message_id', 'message_type')
        }),
        ('Participants', {
            'fields': ('sender', 'recipients')
        }),
        ('Content', {
            'fields': ('subject', 'content', 'sent_datetime')
        }),
        ('Analysis Results', {
            'fields': ('sentiment_score', 'toxicity_score', 'relevance_score')
        }),
        ('Flags and Status', {
            'fields': ('is_privileged', 'contains_pii', 'is_flagged', 'flag_reason')
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


@admin.register(WageHourAnalysis)
class WageHourAnalysisAdmin(admin.ModelAdmin):
    list_display = ('employee_name', 'communications_run', 'total_hours_worked', 'overtime_hours', 'potential_overtime_violations', 'created_at')
    list_filter = ('potential_overtime_violations', 'potential_break_violations', 'potential_meal_violations', 'created_at')
    search_fields = ('employee_name', 'employee_id', 'job_title', 'department')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Employee Information', {
            'fields': ('user', 'communications_run', 'employee_name', 'employee_id', 'job_title', 'department')
        }),
        ('Analysis Period', {
            'fields': ('analysis_start_date', 'analysis_end_date')
        }),
        ('Work Time Analysis', {
            'fields': ('total_hours_worked', 'regular_hours', 'overtime_hours')
        }),
        ('Communication Patterns', {
            'fields': ('early_morning_messages', 'late_evening_messages', 'weekend_messages')
        }),
        ('Wage Calculations', {
            'fields': ('hourly_rate', 'regular_pay', 'overtime_pay', 'total_pay')
        }),
        ('Potential Violations', {
            'fields': ('potential_overtime_violations', 'potential_break_violations', 'potential_meal_violations')
        }),
        ('Analysis Metadata', {
            'fields': ('analysis_metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PolicyComparison)
class PolicyComparisonAdmin(admin.ModelAdmin):
    list_display = ('policy_name', 'policy_type', 'compliance_score', 'best_practices_score', 'created_at')
    list_filter = ('policy_type', 'created_at')
    search_fields = ('policy_name', 'policy_text')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Policy Information', {
            'fields': ('user', 'communications_run', 'policy_name', 'policy_type', 'policy_document')
        }),
        ('Policy Content', {
            'fields': ('policy_text',)
        }),
        ('Comparison Results', {
            'fields': ('compliance_score', 'best_practices_score')
        }),
        ('Findings', {
            'fields': ('violations_found', 'recommendations', 'missing_elements')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EEOCPacket)
class EEOCPacketAdmin(admin.ModelAdmin):
    list_display = ('packet_name', 'complainant_name', 'complaint_type', 'incident_date', 'status', 'evidence_strength_score', 'created_at')
    list_filter = ('complaint_type', 'status', 'incident_date', 'created_at')
    search_fields = ('packet_name', 'complainant_name', 'complaint_summary')
    readonly_fields = ('created_at', 'updated_at', 'submitted_at')
    filter_horizontal = ('relevant_messages', 'supporting_documents')
    
    fieldsets = (
        ('Packet Information', {
            'fields': ('user', 'communications_run', 'packet_name', 'status')
        }),
        ('Complainant Information', {
            'fields': ('complainant_name', 'complainant_title', 'complainant_department')
        }),
        ('Complaint Details', {
            'fields': ('complaint_type', 'incident_date', 'complaint_summary')
        }),
        ('Evidence', {
            'fields': ('relevant_messages', 'supporting_documents')
        }),
        ('Analysis Results', {
            'fields': ('evidence_strength_score', 'timeline_analysis', 'key_findings')
        }),
        ('Generation Metadata', {
            'fields': ('generation_metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'submitted_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CommunicationPattern)
class CommunicationPatternAdmin(admin.ModelAdmin):
    list_display = ('pattern_name', 'pattern_type', 'confidence_score', 'severity_score', 'pattern_start_date', 'pattern_end_date', 'created_at')
    list_filter = ('pattern_type', 'created_at')
    search_fields = ('pattern_name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('supporting_messages',)
    
    fieldsets = (
        ('Pattern Information', {
            'fields': ('user', 'communications_run', 'pattern_type', 'pattern_name', 'description')
        }),
        ('Pattern Participants', {
            'fields': ('involved_personnel',)
        }),
        ('Pattern Metrics', {
            'fields': ('confidence_score', 'severity_score')
        }),
        ('Time Range', {
            'fields': ('pattern_start_date', 'pattern_end_date')
        }),
        ('Supporting Evidence', {
            'fields': ('supporting_messages',)
        }),
        ('Pattern Details', {
            'fields': ('pattern_details',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ComplianceAlert)
class ComplianceAlertAdmin(admin.ModelAdmin):
    list_display = ('alert_title', 'alert_type', 'severity', 'priority', 'status', 'created_at', 'resolved_at')
    list_filter = ('alert_type', 'severity', 'priority', 'status', 'created_at')
    search_fields = ('alert_title', 'alert_description')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('related_messages',)
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('user', 'communications_run', 'alert_type', 'alert_title', 'alert_description')
        }),
        ('Severity and Priority', {
            'fields': ('severity', 'priority')
        }),
        ('Related Evidence', {
            'fields': ('related_messages',)
        }),
        ('Alert Status', {
            'fields': ('status', 'resolution_notes', 'resolved_by', 'resolved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
