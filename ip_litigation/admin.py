from django.contrib import admin
from .models import (
    PatentAnalysisRun, PatentDocument, PatentClaim, PriorArtDocument,
    ClaimChart, PatentLandscape, InfringementAnalysis, ValidityChallenge
)


@admin.register(PatentAnalysisRun)
class PatentAnalysisRunAdmin(admin.ModelAdmin):
    list_display = ('case_name', 'litigation_type', 'technology_area', 'created_at')
    list_filter = ('litigation_type', 'created_at')
    search_fields = ('case_name', 'technology_area')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Case Information', {
            'fields': ('run', 'case_name', 'litigation_type', 'technology_area')
        }),
        ('Patent Sources', {
            'fields': ('patent_sources', 'patents_in_suit')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PatentDocument)
class PatentDocumentAdmin(admin.ModelAdmin):
    list_display = ('patent_number', 'title', 'patent_office', 'status', 'filing_date', 'grant_date')
    list_filter = ('patent_office', 'status', 'filing_date', 'grant_date')
    search_fields = ('patent_number', 'title', 'application_number', 'publication_number')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Patent Identification', {
            'fields': ('file', 'user', 'analysis_run', 'patent_number', 'application_number', 'publication_number')
        }),
        ('Patent Office and Status', {
            'fields': ('patent_office', 'status')
        }),
        ('Patent Metadata', {
            'fields': ('title', 'inventors', 'assignees')
        }),
        ('Important Dates', {
            'fields': ('filing_date', 'publication_date', 'grant_date', 'expiration_date')
        }),
        ('Classification', {
            'fields': ('ipc_classes', 'cpc_classes')
        }),
        ('Content', {
            'fields': ('abstract', 'claims_text', 'description_text'),
            'classes': ('collapse',)
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


@admin.register(PatentClaim)
class PatentClaimAdmin(admin.ModelAdmin):
    list_display = ('patent_document', 'claim_number', 'claim_type', 'element_count', 'complexity_score')
    list_filter = ('claim_type', 'patent_document__patent_office')
    search_fields = ('patent_document__patent_number', 'claim_text')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Claim Information', {
            'fields': ('patent_document', 'user', 'analysis_run', 'claim_number', 'claim_type')
        }),
        ('Claim Content', {
            'fields': ('claim_text',)
        }),
        ('Claim Structure', {
            'fields': ('depends_on_claims', 'claim_elements', 'element_count')
        }),
        ('Analysis Results', {
            'fields': ('complexity_score',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PriorArtDocument)
class PriorArtDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_id', 'title', 'document_type', 'publication_date', 'relevance_score')
    list_filter = ('document_type', 'publication_date')
    search_fields = ('document_id', 'title', 'authors')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Document Information', {
            'fields': ('file', 'user', 'analysis_run', 'document_id', 'document_type')
        }),
        ('Document Metadata', {
            'fields': ('title', 'authors', 'publication_date', 'source')
        }),
        ('Content', {
            'fields': ('abstract', 'content_text')
        }),
        ('Relevance Analysis', {
            'fields': ('relevance_score', 'relevance_explanation', 'art_categories')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ClaimChart)
class ClaimChartAdmin(admin.ModelAdmin):
    list_display = ('chart_name', 'chart_type', 'patent_claim', 'overall_conclusion', 'confidence_score', 'created_at')
    list_filter = ('chart_type', 'overall_conclusion', 'created_at')
    search_fields = ('chart_name', 'target_product', 'analysis_notes')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('supporting_documents',)
    
    fieldsets = (
        ('Chart Information', {
            'fields': ('user', 'analysis_run', 'patent_claim', 'chart_name', 'chart_type')
        }),
        ('Analysis Target', {
            'fields': ('target_product', 'target_prior_art')
        }),
        ('Chart Mappings', {
            'fields': ('element_mappings',)
        }),
        ('Analysis Results', {
            'fields': ('overall_conclusion', 'confidence_score', 'analysis_notes')
        }),
        ('Supporting Evidence', {
            'fields': ('supporting_documents',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PatentLandscape)
class PatentLandscapeAdmin(admin.ModelAdmin):
    list_display = ('landscape_name', 'technology_area', 'total_patents_found', 'created_at')
    list_filter = ('technology_area', 'created_at')
    search_fields = ('landscape_name', 'technology_area', 'search_keywords')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Landscape Information', {
            'fields': ('user', 'analysis_run', 'landscape_name', 'technology_area')
        }),
        ('Search Parameters', {
            'fields': ('search_keywords', 'classification_codes', 'date_range_start', 'date_range_end')
        }),
        ('Analysis Results', {
            'fields': ('total_patents_found', 'key_players', 'technology_trends', 'patent_clusters')
        }),
        ('Landscape Metadata', {
            'fields': ('landscape_metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(InfringementAnalysis)
class InfringementAnalysisAdmin(admin.ModelAdmin):
    list_display = ('analysis_name', 'accused_product', 'infringement_conclusion', 'confidence_level', 'created_at')
    list_filter = ('infringement_conclusion', 'confidence_level', 'literal_infringement', 'doctrine_of_equivalents', 'created_at')
    search_fields = ('analysis_name', 'accused_product', 'analysis_methodology')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('asserted_patents',)
    
    fieldsets = (
        ('Analysis Information', {
            'fields': ('user', 'analysis_run', 'analysis_name', 'accused_product')
        }),
        ('Asserted Patents', {
            'fields': ('asserted_patents',)
        }),
        ('Analysis Methodology', {
            'fields': ('analysis_methodology',)
        }),
        ('Infringement Findings', {
            'fields': ('literal_infringement', 'doctrine_of_equivalents')
        }),
        ('Overall Conclusion', {
            'fields': ('infringement_conclusion', 'confidence_level')
        }),
        ('Detailed Analysis', {
            'fields': ('detailed_findings', 'recommendations'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ValidityChallenge)
class ValidityChallengeAdmin(admin.ModelAdmin):
    list_display = ('challenge_name', 'target_patent', 'challenge_strength', 'success_likelihood', 'created_at')
    list_filter = ('challenge_strength', 'created_at')
    search_fields = ('challenge_name', 'target_patent__patent_number')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('prior_art_references',)
    
    fieldsets = (
        ('Challenge Information', {
            'fields': ('user', 'analysis_run', 'target_patent', 'challenge_name')
        }),
        ('Challenge Grounds', {
            'fields': ('challenge_grounds',)
        }),
        ('Prior Art References', {
            'fields': ('prior_art_references',)
        }),
        ('Invalidity Analysis', {
            'fields': ('anticipation_analysis', 'obviousness_analysis')
        }),
        ('Challenge Assessment', {
            'fields': ('challenge_strength', 'success_likelihood')
        }),
        ('Detailed Analysis', {
            'fields': ('detailed_analysis',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
