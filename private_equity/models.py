from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
import uuid

User = get_user_model()


class DueDiligenceRun(models.Model):
    """
    Represents a due diligence run for M&A or Private Equity transactions.
    Extends the core Run concept for DD-specific workflows.
    """
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

    def __str__(self):
        return f"{self.deal_name} - {self.target_company}"


class DocumentClassification(models.Model):
    """
    Stores AI-based classification results for uploaded documents.
    """
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
