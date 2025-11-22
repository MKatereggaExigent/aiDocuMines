from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.storage import default_storage
import uuid
import json

User = get_user_model()


class DueDiligenceRun(models.Model):
    """
    Represents a due diligence run for M&A or Private Equity transactions.
    Extends the core Run concept for DD-specific workflows.
    """
    # Multi-tenancy
    client = models.ForeignKey('custom_authentication.Client', on_delete=models.CASCADE, related_name='pe_dd_runs')

    run = models.OneToOneField('core.Run', on_delete=models.CASCADE, related_name='due_diligence')
    deal_name = models.CharField(max_length=255, help_text="Name of the deal/transaction")
    target_company = models.CharField(max_length=255, help_text="Target company name")
    deal_type = models.CharField(
        max_length=50,
        choices=[
            ('acquisition', 'Acquisition'),
            ('merger', 'Merger'),
            ('investment', 'Investment'),
            ('divestiture', 'Divestiture')
        ],
        default='acquisition'
    )
    data_room_source = models.CharField(
        max_length=100,
        choices=[
            ('google_drive', 'Google Drive'),
            ('sharepoint', 'SharePoint'),
            ('box', 'Box'),
            ('dropbox', 'Dropbox'),
            ('manual_upload', 'Manual Upload')
        ],
        default='manual_upload'
    )
    deal_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    expected_close_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'private_equity_due_diligence_run'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', '-created_at']),
            models.Index(fields=['client', 'deal_name']),
        ]

    def __str__(self):
        return f"{self.deal_name} - {self.target_company}"


class DocumentClassification(models.Model):
    """
    Stores AI-based classification results for uploaded documents.
    """
    # Multi-tenancy
    client = models.ForeignKey('custom_authentication.Client', on_delete=models.CASCADE, related_name='pe_doc_classifications')

    file = models.ForeignKey('core.File', on_delete=models.CASCADE, related_name='pe_classifications')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pe_document_classifications')
    due_diligence_run = models.ForeignKey(DueDiligenceRun, on_delete=models.CASCADE, related_name='document_classifications')
    
    document_type = models.CharField(
        max_length=100,
        choices=[
            ('nda', 'Non-Disclosure Agreement'),
            ('supplier_contract', 'Supplier Contract'),
            ('employment_agreement', 'Employment Agreement'),
            ('lease_agreement', 'Lease Agreement'),
            ('ip_document', 'Intellectual Property Document'),
            ('privacy_policy', 'Privacy Policy'),
            ('financial_statement', 'Financial Statement'),
            ('audit_report', 'Audit Report'),
            ('insurance_policy', 'Insurance Policy'),
            ('regulatory_filing', 'Regulatory Filing'),
            ('other', 'Other')
        ]
    )
    confidence_score = models.FloatField(help_text="AI confidence score (0.0 to 1.0)")
    classification_metadata = models.JSONField(default=dict, blank=True, help_text="Additional classification details")
    is_verified = models.BooleanField(default=False, help_text="Human verification status")
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pe_verified_classifications')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'private_equity_document_classification'
        unique_together = ['file', 'user']
        ordering = ['-confidence_score']

    def __str__(self):
        return f"{self.file.filename} - {self.get_document_type_display()} ({self.confidence_score:.2f})"


class RiskClause(models.Model):
    """
    Stores extracted risky clauses from documents with risk assessment.
    """
    # Multi-tenancy
    client = models.ForeignKey('custom_authentication.Client', on_delete=models.CASCADE, related_name='pe_risk_clauses')

    file = models.ForeignKey('core.File', on_delete=models.CASCADE, related_name='pe_risk_clauses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pe_risk_clauses')
    due_diligence_run = models.ForeignKey(DueDiligenceRun, on_delete=models.CASCADE, related_name='risk_clauses')
    
    clause_type = models.CharField(
        max_length=100,
        choices=[
            ('change_of_control', 'Change of Control'),
            ('assignment', 'Assignment'),
            ('termination', 'Termination'),
            ('indemnity', 'Indemnity'),
            ('non_compete', 'Non-Compete'),
            ('data_privacy', 'Data Privacy'),
            ('force_majeure', 'Force Majeure'),
            ('liability_cap', 'Liability Cap'),
            ('governing_law', 'Governing Law'),
            ('dispute_resolution', 'Dispute Resolution')
        ]
    )
    clause_text = models.TextField(help_text="Extracted clause text")
    risk_level = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low Risk'),
            ('medium', 'Medium Risk'),
            ('high', 'High Risk'),
            ('critical', 'Critical Risk')
        ]
    )
    page_number = models.IntegerField(help_text="Page number where clause was found")
    position_start = models.IntegerField(null=True, blank=True, help_text="Character start position")
    position_end = models.IntegerField(null=True, blank=True, help_text="Character end position")
    risk_explanation = models.TextField(blank=True, help_text="Explanation of why this clause is risky")
    mitigation_suggestions = models.TextField(blank=True, help_text="Suggested mitigation strategies")
    is_reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pe_reviewed_clauses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'private_equity_risk_clause'
        ordering = ['-risk_level', 'page_number']

    def __str__(self):
        return f"{self.get_clause_type_display()} - {self.get_risk_level_display()}"


class FindingsReport(models.Model):
    """
    Comprehensive findings report for a due diligence run.
    """
    # Multi-tenancy
    client = models.ForeignKey('custom_authentication.Client', on_delete=models.CASCADE, related_name='pe_findings_reports')

    due_diligence_run = models.ForeignKey(DueDiligenceRun, on_delete=models.CASCADE, related_name='findings_reports')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pe_findings_reports')
    
    report_name = models.CharField(max_length=255, default="Due Diligence Findings Report")
    executive_summary = models.TextField(blank=True, help_text="Executive summary of findings")
    
    # Structured report data
    document_summary = models.JSONField(default=dict, help_text="Summary of document types and counts")
    risk_summary = models.JSONField(default=dict, help_text="Summary of risk clauses by type and level")
    key_findings = models.JSONField(default=list, help_text="List of key findings")
    recommendations = models.JSONField(default=list, help_text="List of recommendations")
    
    # Report metadata
    total_documents_reviewed = models.IntegerField(default=0)
    total_risk_clauses_found = models.IntegerField(default=0)
    high_risk_items_count = models.IntegerField(default=0)
    
    # Report status
    status = models.CharField(
        max_length=50,
        choices=[
            ('draft', 'Draft'),
            ('review', 'Under Review'),
            ('final', 'Final'),
            ('archived', 'Archived')
        ],
        default='draft'
    )
    
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pe_finalized_reports')

    class Meta:
        db_table = 'private_equity_findings_report'
        ordering = ['-generated_at']

    def __str__(self):
        return f"{self.report_name} - {self.due_diligence_run.deal_name}"


class DataRoomConnector(models.Model):
    """
    Configuration for connecting to external data rooms (Google Drive, SharePoint, etc.).
    """
    # Multi-tenancy
    client = models.ForeignKey('custom_authentication.Client', on_delete=models.CASCADE, related_name='pe_data_room_connectors')

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pe_data_room_connectors')
    due_diligence_run = models.ForeignKey(DueDiligenceRun, on_delete=models.CASCADE, related_name='data_room_connectors')
    
    connector_type = models.CharField(
        max_length=50,
        choices=[
            ('google_drive', 'Google Drive'),
            ('sharepoint', 'SharePoint'),
            ('box', 'Box'),
            ('dropbox', 'Dropbox')
        ]
    )
    connector_name = models.CharField(max_length=255, help_text="Human-readable name for this connector")
    
    # Connection configuration (encrypted)
    connection_config = models.JSONField(default=dict, help_text="Encrypted connection configuration")
    
    # Sync status
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pending'),
            ('syncing', 'Syncing'),
            ('completed', 'Completed'),
            ('failed', 'Failed')
        ],
        default='pending'
    )
    sync_error_message = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'private_equity_data_room_connector'
        unique_together = ['user', 'due_diligence_run', 'connector_name']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.connector_name} ({self.get_connector_type_display()})"


# ═══════════════════════════════════════════════════════════════
# 🔄 COMPREHENSIVE SERVICE OUTPUT MODELS
# ═══════════════════════════════════════════════════════════════

class ServiceExecution(models.Model):
    """
    Tracks execution of all Private Equity services with comprehensive metadata.
    """
    SERVICE_TYPES = [
        # Core PE Services
        ('pe-create-dd-run', 'Create Due Diligence Run'),
        ('pe-classify-documents', 'Auto Classify & Dedup Documents'),
        ('pe-extract-risk-clauses', 'Clause & Obligation Extraction'),
        ('pe-generate-findings', 'Generate Findings Report'),
        ('pe-sync-data-room', 'Data Room Sync'),

        # AI-Enhanced PE Services
        ('pe-document-structure', 'Document Structure Analysis'),
        ('pe-semantic-search', 'Investment Document Search'),
        ('pe-document-qa', 'Due Diligence Q&A'),
        ('pe-file-insights', 'Portfolio File Insights'),
        ('pe-project-summary', 'Deal Project Summary'),
        ('pe-document-anonymization', 'Confidential Deal Anonymization'),
        ('pe-ocr-financial', 'Financial Document OCR'),
    ]

    EXECUTION_STATUS = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    OUTPUT_TYPES = [
        ('document', 'Document'),
        ('pdf', 'PDF'),
        ('text', 'Text'),
        ('json', 'JSON Data'),
        ('data', 'Data File'),
        ('analytics', 'Analytics'),
        ('report', 'Report'),
        ('chart', 'Chart'),
        ('dashboard', 'Dashboard'),
        ('excel', 'Excel'),
        ('matrix', 'Matrix'),
        ('package', 'Package'),
    ]

    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Multi-tenancy
    client = models.ForeignKey('custom_authentication.Client', on_delete=models.CASCADE, related_name='pe_service_executions')

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pe_service_executions')
    due_diligence_run = models.ForeignKey(DueDiligenceRun, on_delete=models.CASCADE, related_name='service_executions')

    # Service details
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPES)
    service_name = models.CharField(max_length=255, help_text="Human-readable service name")
    service_version = models.CharField(max_length=20, default='1.0')

    # Execution tracking
    status = models.CharField(max_length=20, choices=EXECUTION_STATUS, default='pending')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    execution_time_seconds = models.IntegerField(null=True, blank=True)

    # Input/Output tracking
    input_files = models.ManyToManyField('core.File', blank=True, related_name='pe_service_inputs')
    input_parameters = models.JSONField(default=dict, help_text="Service input parameters")
    output_type = models.CharField(max_length=20, choices=OUTPUT_TYPES, default='json')
    output_count = models.IntegerField(default=0, help_text="Number of output files generated")

    # Error handling
    error_message = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)

    # Metadata
    execution_metadata = models.JSONField(default=dict, help_text="Additional execution metadata")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'private_equity_service_execution'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'service_type']),
            models.Index(fields=['due_diligence_run', 'status']),
            models.Index(fields=['started_at']),
        ]

    def __str__(self):
        return f"{self.service_name} - {self.get_status_display()}"

    @property
    def duration(self):
        """Calculate execution duration"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class ServiceOutput(models.Model):
    """
    Stores individual output files/data from service executions.
    """
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Multi-tenancy
    client = models.ForeignKey('custom_authentication.Client', on_delete=models.CASCADE, related_name='pe_service_outputs')

    service_execution = models.ForeignKey(ServiceExecution, on_delete=models.CASCADE, related_name='outputs')

    # Output details
    output_name = models.CharField(max_length=255, help_text="Name/title of the output")
    output_type = models.CharField(max_length=20, choices=ServiceExecution.OUTPUT_TYPES)
    file_extension = models.CharField(max_length=10, blank=True, help_text="File extension if applicable")
    mime_type = models.CharField(max_length=100, blank=True)

    # File storage
    output_file = models.FileField(upload_to='pe_service_outputs/%Y/%m/%d/', null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True, help_text="File size in bytes")

    # Data storage (for non-file outputs)
    output_data = models.JSONField(null=True, blank=True, help_text="Structured data output")
    output_text = models.TextField(blank=True, help_text="Text-based output")

    # URLs and access
    download_url = models.URLField(blank=True, help_text="Direct download URL")
    preview_url = models.URLField(blank=True, help_text="Preview URL")

    # Metadata
    output_metadata = models.JSONField(default=dict, help_text="Additional output metadata")
    is_primary = models.BooleanField(default=False, help_text="Primary output for the service")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'private_equity_service_output'
        ordering = ['-is_primary', '-created_at']
        indexes = [
            models.Index(fields=['service_execution', 'output_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.output_name} ({self.get_output_type_display()})"

    @property
    def formatted_size(self):
        """Return human-readable file size"""
        if not self.file_size:
            return "Unknown"

        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"
