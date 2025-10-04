from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
import uuid

User = get_user_model()


class MassClaimsRun(models.Model):
    """
    Represents a mass claims or class action case management run.
    """
    run = models.OneToOneField('core.Run', on_delete=models.CASCADE, related_name='mass_claims')
    case_name = models.CharField(max_length=255, help_text="Name of the class action case")
    case_number = models.CharField(max_length=100, help_text="Court case number")
    court_jurisdiction = models.CharField(max_length=255, blank=True, help_text="Court jurisdiction")
    
    case_type = models.CharField(
        max_length=100,
        choices=[
            ('consumer_protection', 'Consumer Protection'),
            ('securities', 'Securities'),
            ('antitrust', 'Antitrust'),
            ('employment', 'Employment'),
            ('data_breach', 'Data Breach'),
            ('product_liability', 'Product Liability'),
            ('environmental', 'Environmental'),
            ('other', 'Other')
        ],
        default='consumer_protection'
    )
    
    claim_deadline = models.DateTimeField(help_text="Deadline for claim submissions")
    settlement_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Case status
    status = models.CharField(
        max_length=50,
        choices=[
            ('intake', 'Intake Phase'),
            ('discovery', 'Discovery Phase'),
            ('settlement', 'Settlement Phase'),
            ('distribution', 'Distribution Phase'),
            ('closed', 'Closed')
        ],
        default='intake'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'class_actions_mass_claims_run'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.case_name} - {self.case_number}"


class IntakeForm(models.Model):
    """
    Stores intake form submissions from claimants.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ca_intake_forms')
    mass_claims_run = models.ForeignKey(MassClaimsRun, on_delete=models.CASCADE, related_name='intake_forms')
    
    # Claimant identification
    claimant_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Form data (flexible JSON structure)
    claimant_data = models.JSONField(default=dict, help_text="Flexible claimant form data")
    
    # Deduplication
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='duplicates')
    duplicate_score = models.FloatField(null=True, blank=True, help_text="Similarity score for duplicate detection")
    
    # Processing status
    processing_status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pending Review'),
            ('processing', 'Processing'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('duplicate', 'Marked as Duplicate')
        ],
        default='pending'
    )
    
    # Validation
    is_valid = models.BooleanField(default=True)
    validation_errors = models.JSONField(default=list, blank=True)
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ca_processed_forms')

    class Meta:
        db_table = 'class_actions_intake_form'
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Intake Form {self.claimant_id} - {self.mass_claims_run.case_name}"


class EvidenceDocument(models.Model):
    """
    Represents evidence documents with culling and relevance scoring.
    """
    file = models.ForeignKey('core.File', on_delete=models.CASCADE, related_name='ca_evidence')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ca_evidence_documents')
    mass_claims_run = models.ForeignKey(MassClaimsRun, on_delete=models.CASCADE, related_name='evidence_documents')
    
    evidence_type = models.CharField(
        max_length=100,
        choices=[
            ('email', 'Email'),
            ('chat_log', 'Chat Log'),
            ('document', 'Document'),
            ('financial_record', 'Financial Record'),
            ('communication', 'Communication'),
            ('contract', 'Contract'),
            ('policy', 'Policy'),
            ('other', 'Other')
        ]
    )
    
    # Culling and relevance
    is_culled = models.BooleanField(default=False, help_text="Whether document was culled (excluded)")
    cull_reason = models.TextField(blank=True, help_text="Reason for culling")
    relevance_score = models.FloatField(null=True, blank=True, help_text="AI-generated relevance score (0.0-1.0)")
    
    # Content analysis
    contains_pii = models.BooleanField(default=False)
    privilege_status = models.CharField(
        max_length=50,
        choices=[
            ('none', 'No Privilege'),
            ('attorney_client', 'Attorney-Client'),
            ('work_product', 'Work Product'),
            ('other', 'Other Privilege')
        ],
        default='none'
    )
    
    # Processing metadata
    processing_metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'class_actions_evidence_document'
        ordering = ['-relevance_score', '-created_at']

    def __str__(self):
        return f"Evidence: {self.file.filename} - {self.get_evidence_type_display()}"


class PIIRedaction(models.Model):
    """
    Stores PII redaction information for documents.
    """
    file = models.ForeignKey('core.File', on_delete=models.CASCADE, related_name='ca_pii_redactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ca_pii_redactions')
    mass_claims_run = models.ForeignKey(MassClaimsRun, on_delete=models.CASCADE, related_name='pii_redactions')
    
    pii_type = models.CharField(
        max_length=50,
        choices=[
            ('name', 'Personal Name'),
            ('email', 'Email Address'),
            ('phone', 'Phone Number'),
            ('ssn', 'Social Security Number'),
            ('address', 'Physical Address'),
            ('credit_card', 'Credit Card Number'),
            ('bank_account', 'Bank Account Number'),
            ('driver_license', 'Driver License'),
            ('passport', 'Passport Number'),
            ('other', 'Other PII')
        ]
    )
    
    original_text = models.TextField(help_text="Original text containing PII")
    redacted_text = models.TextField(help_text="Text with PII redacted")
    
    # Location information
    page_number = models.IntegerField(help_text="Page number where PII was found")
    position_start = models.IntegerField(null=True, blank=True)
    position_end = models.IntegerField(null=True, blank=True)
    
    # Confidence and verification
    confidence_score = models.FloatField(help_text="AI confidence in PII detection (0.0-1.0)")
    is_verified = models.BooleanField(default=False, help_text="Human verification of redaction")
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ca_verified_redactions')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'class_actions_pii_redaction'
        ordering = ['page_number', 'position_start']

    def __str__(self):
        return f"PII Redaction: {self.get_pii_type_display()} in {self.file.filename}"


class ExhibitPackage(models.Model):
    """
    Represents a package of documents for exhibit production with Bates stamping.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ca_exhibit_packages')
    mass_claims_run = models.ForeignKey(MassClaimsRun, on_delete=models.CASCADE, related_name='exhibit_packages')
    
    package_name = models.CharField(max_length=255, help_text="Name of the exhibit package")
    description = models.TextField(blank=True, help_text="Description of the package contents")
    
    # Files in the package
    files = models.ManyToManyField('core.File', related_name='ca_exhibit_packages')
    
    # Bates numbering
    bates_prefix = models.CharField(max_length=20, default="EXHIBIT", help_text="Bates number prefix")
    bates_start = models.CharField(max_length=50, help_text="Starting Bates number")
    bates_end = models.CharField(max_length=50, help_text="Ending Bates number")
    total_pages = models.IntegerField(default=0, help_text="Total pages in package")
    
    # Package status
    status = models.CharField(
        max_length=50,
        choices=[
            ('draft', 'Draft'),
            ('processing', 'Processing'),
            ('ready', 'Ready for Production'),
            ('produced', 'Produced'),
            ('archived', 'Archived')
        ],
        default='draft'
    )
    
    # Production metadata
    production_metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    produced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'class_actions_exhibit_package'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.package_name} ({self.bates_start} - {self.bates_end})"


class SettlementTracking(models.Model):
    """
    Tracks settlement and notice information for mass claims.
    """
    mass_claims_run = models.ForeignKey(MassClaimsRun, on_delete=models.CASCADE, related_name='settlement_tracking')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ca_settlement_tracking')
    
    # Settlement details
    settlement_type = models.CharField(
        max_length=50,
        choices=[
            ('monetary', 'Monetary Settlement'),
            ('injunctive', 'Injunctive Relief'),
            ('mixed', 'Mixed Settlement'),
            ('other', 'Other')
        ],
        default='monetary'
    )
    
    total_settlement_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    attorney_fees = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    administration_costs = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    net_settlement_fund = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Notice information
    notice_type = models.CharField(
        max_length=50,
        choices=[
            ('publication', 'Publication Notice'),
            ('direct_mail', 'Direct Mail'),
            ('email', 'Email Notice'),
            ('website', 'Website Notice'),
            ('combined', 'Combined Methods')
        ],
        default='publication'
    )
    
    notice_deadline = models.DateTimeField(null=True, blank=True)
    objection_deadline = models.DateTimeField(null=True, blank=True)
    opt_out_deadline = models.DateTimeField(null=True, blank=True)
    
    # Distribution tracking
    total_eligible_claimants = models.IntegerField(default=0)
    total_approved_claims = models.IntegerField(default=0)
    total_distributed_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Status
    status = models.CharField(
        max_length=50,
        choices=[
            ('pending_approval', 'Pending Court Approval'),
            ('approved', 'Court Approved'),
            ('notice_period', 'Notice Period'),
            ('distribution', 'Distribution Phase'),
            ('completed', 'Completed')
        ],
        default='pending_approval'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'class_actions_settlement_tracking'
        ordering = ['-created_at']

    def __str__(self):
        return f"Settlement Tracking - {self.mass_claims_run.case_name}"


class ClaimantCommunication(models.Model):
    """
    Tracks communications with claimants throughout the process.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ca_claimant_communications')
    mass_claims_run = models.ForeignKey(MassClaimsRun, on_delete=models.CASCADE, related_name='claimant_communications')
    intake_form = models.ForeignKey(IntakeForm, on_delete=models.CASCADE, related_name='communications')
    
    communication_type = models.CharField(
        max_length=50,
        choices=[
            ('email', 'Email'),
            ('mail', 'Physical Mail'),
            ('phone', 'Phone Call'),
            ('sms', 'SMS'),
            ('portal', 'Web Portal Message')
        ]
    )
    
    subject = models.CharField(max_length=255, blank=True)
    message_content = models.TextField()
    
    # Status tracking
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    # Response tracking
    response_content = models.TextField(blank=True)
    requires_follow_up = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'class_actions_claimant_communication'
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.get_communication_type_display()} - {self.intake_form.claimant_id}"
