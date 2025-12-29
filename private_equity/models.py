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


# ═══════════════════════════════════════════════════════════════
# 💼 PE VALUE METRICS MODELS - Deal Velocity, Checklists, Obligations
# ═══════════════════════════════════════════════════════════════

class ClosingChecklist(models.Model):
    """
    Closing checklist for deal execution - tracks items needed before close.
    Supports checklist automation and signature/status tracking.
    """
    CHECKLIST_CATEGORIES = [
        ('legal', 'Legal/Corporate'),
        ('financial', 'Financial'),
        ('regulatory', 'Regulatory'),
        ('operational', 'Operational'),
        ('hr', 'Human Resources'),
        ('ip', 'Intellectual Property'),
        ('tax', 'Tax'),
        ('insurance', 'Insurance'),
        ('real_estate', 'Real Estate'),
        ('it', 'IT/Technology'),
        ('environmental', 'Environmental'),
        ('other', 'Other'),
    ]

    ITEM_STATUS = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('pending_review', 'Pending Review'),
        ('pending_signature', 'Pending Signature'),
        ('completed', 'Completed'),
        ('blocked', 'Blocked'),
        ('not_applicable', 'Not Applicable'),
    ]

    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    # Multi-tenancy
    client = models.ForeignKey('custom_authentication.Client', on_delete=models.CASCADE, related_name='pe_closing_checklists')

    due_diligence_run = models.ForeignKey(DueDiligenceRun, on_delete=models.CASCADE, related_name='closing_checklists')

    # Item details
    item_name = models.CharField(max_length=500, help_text="Checklist item description")
    category = models.CharField(max_length=50, choices=CHECKLIST_CATEGORIES, default='legal')
    priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS, default='medium')

    # Status tracking
    status = models.CharField(max_length=30, choices=ITEM_STATUS, default='not_started')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pe_assigned_checklist_items')

    # Dates
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)

    # Dependencies and blocking
    depends_on = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='dependents')
    blocker_notes = models.TextField(blank=True, help_text="Notes if item is blocked")

    # Documents and signatures
    related_document = models.ForeignKey('core.File', on_delete=models.SET_NULL, null=True, blank=True, related_name='pe_checklist_items')
    requires_signature = models.BooleanField(default=False)
    signature_obtained = models.BooleanField(default=False)
    signatory_name = models.CharField(max_length=255, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    # Ordering within checklist
    order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='pe_created_checklist_items')

    class Meta:
        db_table = 'private_equity_closing_checklist'
        ordering = ['order', 'priority', 'due_date']
        indexes = [
            models.Index(fields=['client', 'due_diligence_run', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['category', 'status']),
        ]

    def __str__(self):
        return f"{self.item_name} - {self.get_status_display()}"

    @property
    def is_overdue(self):
        """Check if item is overdue"""
        from django.utils import timezone
        if self.due_date and self.status not in ['completed', 'not_applicable']:
            return self.due_date < timezone.now().date()
        return False


class PostCloseObligation(models.Model):
    """
    Post-close obligations tracker - tracks consents, filings, covenants after deal closure.
    """
    OBLIGATION_TYPES = [
        ('consent', 'Consent Required'),
        ('filing', 'Regulatory Filing'),
        ('covenant', 'Covenant Compliance'),
        ('notification', 'Notification'),
        ('integration', 'Integration Task'),
        ('payment', 'Payment/Earnout'),
        ('reporting', 'Reporting Requirement'),
        ('other', 'Other'),
    ]

    OBLIGATION_STATUS = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('waived', 'Waived'),
    ]

    FREQUENCY = [
        ('one_time', 'One-Time'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
        ('ongoing', 'Ongoing'),
    ]

    # Multi-tenancy
    client = models.ForeignKey('custom_authentication.Client', on_delete=models.CASCADE, related_name='pe_post_close_obligations')

    due_diligence_run = models.ForeignKey(DueDiligenceRun, on_delete=models.CASCADE, related_name='post_close_obligations')

    # Obligation details
    obligation_name = models.CharField(max_length=500)
    obligation_type = models.CharField(max_length=50, choices=OBLIGATION_TYPES)
    description = models.TextField(blank=True)

    # Source document/clause
    source_document = models.ForeignKey('core.File', on_delete=models.SET_NULL, null=True, blank=True, related_name='pe_source_obligations')
    source_clause = models.TextField(blank=True, help_text="Relevant clause text")

    # Status and tracking
    status = models.CharField(max_length=30, choices=OBLIGATION_STATUS, default='pending')
    frequency = models.CharField(max_length=20, choices=FREQUENCY, default='one_time')

    # Dates
    effective_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    next_due_date = models.DateField(null=True, blank=True, help_text="For recurring obligations")

    # Responsibility
    responsible_party = models.CharField(max_length=255, blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pe_assigned_obligations')

    # Risk and impact
    risk_level = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], default='medium')
    non_compliance_impact = models.TextField(blank=True, help_text="Impact if obligation is not met")

    # Notes and evidence
    notes = models.TextField(blank=True)
    evidence_file = models.ForeignKey('core.File', on_delete=models.SET_NULL, null=True, blank=True, related_name='pe_obligation_evidence')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='pe_created_obligations')

    class Meta:
        db_table = 'private_equity_post_close_obligation'
        ordering = ['due_date', 'risk_level']
        indexes = [
            models.Index(fields=['client', 'due_diligence_run', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['obligation_type', 'status']),
        ]

    def __str__(self):
        return f"{self.obligation_name} - {self.get_status_display()}"


class DealVelocityMetrics(models.Model):
    """
    Tracks deal velocity metrics - time spent in each phase, bottlenecks, and performance.
    Used for identifying bottlenecks and improving deal process repeatability.
    """
    DEAL_PHASES = [
        ('initial_review', 'Initial Review'),
        ('nda_execution', 'NDA Execution'),
        ('preliminary_dd', 'Preliminary Due Diligence'),
        ('loi_negotiation', 'LOI Negotiation'),
        ('full_dd', 'Full Due Diligence'),
        ('definitive_docs', 'Definitive Documentation'),
        ('regulatory_approval', 'Regulatory Approval'),
        ('closing', 'Closing'),
        ('post_close', 'Post-Close Integration'),
    ]

    # Multi-tenancy
    client = models.ForeignKey('custom_authentication.Client', on_delete=models.CASCADE, related_name='pe_deal_velocity_metrics')

    due_diligence_run = models.ForeignKey(DueDiligenceRun, on_delete=models.CASCADE, related_name='velocity_metrics')

    # Phase tracking
    phase = models.CharField(max_length=50, choices=DEAL_PHASES)
    phase_start_date = models.DateTimeField()
    phase_end_date = models.DateTimeField(null=True, blank=True)

    # Time metrics
    planned_duration_days = models.IntegerField(null=True, blank=True)
    actual_duration_days = models.IntegerField(null=True, blank=True)

    # Bottleneck tracking
    is_bottleneck = models.BooleanField(default=False)
    bottleneck_reason = models.TextField(blank=True)
    bottleneck_resolved = models.BooleanField(default=False)
    bottleneck_resolution = models.TextField(blank=True)

    # Resource tracking
    team_members_involved = models.IntegerField(default=1)
    external_parties_involved = models.IntegerField(default=0)

    # Quality metrics
    issues_identified = models.IntegerField(default=0)
    issues_resolved = models.IntegerField(default=0)
    documents_reviewed = models.IntegerField(default=0)

    # Notes
    notes = models.TextField(blank=True)
    key_milestones = models.JSONField(default=list, help_text="Key milestones achieved in this phase")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'private_equity_deal_velocity_metrics'
        ordering = ['due_diligence_run', 'phase_start_date']
        unique_together = ['due_diligence_run', 'phase']
        indexes = [
            models.Index(fields=['client', 'due_diligence_run']),
            models.Index(fields=['phase', 'is_bottleneck']),
        ]

    def __str__(self):
        return f"{self.due_diligence_run.deal_name} - {self.get_phase_display()}"

    @property
    def variance_days(self):
        """Calculate variance between planned and actual duration"""
        if self.planned_duration_days and self.actual_duration_days:
            return self.actual_duration_days - self.planned_duration_days
        return None

    @property
    def is_delayed(self):
        """Check if phase took longer than planned"""
        variance = self.variance_days
        return variance is not None and variance > 0


class ClauseLibrary(models.Model):
    """
    Library of standard clauses for repeatable deal processes.
    Supports clause libraries and playbooks for consistent deal execution.
    """
    CLAUSE_CATEGORIES = [
        ('rep_warranty', 'Representations & Warranties'),
        ('indemnification', 'Indemnification'),
        ('covenants', 'Covenants'),
        ('conditions', 'Conditions Precedent'),
        ('termination', 'Termination'),
        ('confidentiality', 'Confidentiality'),
        ('non_compete', 'Non-Compete'),
        ('ip', 'Intellectual Property'),
        ('employment', 'Employment'),
        ('tax', 'Tax'),
        ('regulatory', 'Regulatory'),
        ('dispute', 'Dispute Resolution'),
        ('other', 'Other'),
    ]

    RISK_LEVELS = [
        ('standard', 'Standard/Neutral'),
        ('buyer_favorable', 'Buyer Favorable'),
        ('seller_favorable', 'Seller Favorable'),
        ('aggressive', 'Aggressive'),
        ('conservative', 'Conservative'),
    ]

    # Multi-tenancy
    client = models.ForeignKey('custom_authentication.Client', on_delete=models.CASCADE, related_name='pe_clause_libraries')

    # Clause details
    clause_name = models.CharField(max_length=255)
    clause_category = models.CharField(max_length=50, choices=CLAUSE_CATEGORIES)
    clause_text = models.TextField()

    # Classification
    risk_position = models.CharField(max_length=30, choices=RISK_LEVELS, default='standard')
    deal_types = models.JSONField(default=list, help_text="Applicable deal types: ['acquisition', 'merger', etc.]")

    # Usage tracking
    usage_count = models.IntegerField(default=0)
    last_used_date = models.DateField(null=True, blank=True)

    # Versioning
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    parent_clause = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='versions')

    # Notes and guidance
    usage_notes = models.TextField(blank=True, help_text="When to use this clause")
    negotiation_tips = models.TextField(blank=True, help_text="Tips for negotiating this clause")

    # Tags for searchability
    tags = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='pe_created_clauses')

    class Meta:
        db_table = 'private_equity_clause_library'
        ordering = ['clause_category', 'clause_name']
        indexes = [
            models.Index(fields=['client', 'clause_category']),
            models.Index(fields=['is_active', 'usage_count']),
        ]

    def __str__(self):
        return f"{self.clause_name} (v{self.version})"
