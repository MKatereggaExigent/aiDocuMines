from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.models import Run, File
from .models import (
    ComplianceRun, RegulatoryRequirement, PolicyMapping, DSARRequest,
    DataInventory, RedactionTask, ComplianceAlert
)

User = get_user_model()


class ComplianceRunSerializer(serializers.ModelSerializer):
    """
    Serializer for ComplianceRun model.
    """
    run_id = serializers.IntegerField(write_only=True, help_text="ID of the core Run to associate with")
    
    class Meta:
        model = ComplianceRun
        fields = [
            'id', 'run_id', 'compliance_framework', 'organization_name', 'assessment_scope',
            'applicable_regulations', 'jurisdiction', 'assessment_start_date', 'assessment_end_date',
            'compliance_officer', 'legal_counsel', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        run_id = validated_data.pop('run_id')
        user = self.context['request'].user
        run = Run.objects.get(id=run_id, user=user)
        return ComplianceRun.objects.create(run=run, client=user.client, **validated_data)
    
    def validate_assessment_dates(self, data):
        """Validate assessment date range"""
        start_date = data.get('assessment_start_date')
        end_date = data.get('assessment_end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("Assessment start date must be before end date")
        
        return data


class RegulatoryRequirementSerializer(serializers.ModelSerializer):
    """
    Serializer for RegulatoryRequirement model.
    """
    compliance_run_id = serializers.IntegerField(write_only=True, help_text="ID of the ComplianceRun")
    
    class Meta:
        model = RegulatoryRequirement
        fields = [
            'id', 'compliance_run_id', 'requirement_id', 'requirement_title', 'requirement_text',
            'category', 'compliance_status', 'risk_level', 'implementation_notes',
            'remediation_plan', 'responsible_party', 'due_date', 'last_reviewed',
            'next_review', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        compliance_run_id = validated_data.pop('compliance_run_id')
        
        user = self.context['request'].user
        compliance_run = ComplianceRun.objects.get(id=compliance_run_id, run__user=user)
        
        return RegulatoryRequirement.objects.create(
            user=user,
            compliance_run=compliance_run,
            **validated_data
        )
    
    def validate_requirement_id(self, value):
        """Validate requirement ID format"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Requirement ID is required")
        return value.strip().upper()


class PolicyMappingSerializer(serializers.ModelSerializer):
    """
    Serializer for PolicyMapping model.
    """
    compliance_run_id = serializers.IntegerField(write_only=True, help_text="ID of the ComplianceRun")
    regulatory_requirement_id = serializers.IntegerField(write_only=True, help_text="ID of the RegulatoryRequirement")
    policy_document_id = serializers.IntegerField(write_only=True, help_text="ID of the policy File")
    
    class Meta:
        model = PolicyMapping
        fields = [
            'id', 'compliance_run_id', 'regulatory_requirement_id', 'policy_document_id',
            'policy_name', 'policy_section', 'mapping_strength', 'gap_analysis',
            'recommendations', 'mapping_confidence', 'mapping_metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        compliance_run_id = validated_data.pop('compliance_run_id')
        regulatory_requirement_id = validated_data.pop('regulatory_requirement_id')
        policy_document_id = validated_data.pop('policy_document_id')
        
        user = self.context['request'].user
        compliance_run = ComplianceRun.objects.get(id=compliance_run_id, run__user=user)
        regulatory_requirement = RegulatoryRequirement.objects.get(id=regulatory_requirement_id, user=user)
        policy_document = File.objects.get(id=policy_document_id, user=user)
        
        return PolicyMapping.objects.create(
            user=user,
            compliance_run=compliance_run,
            regulatory_requirement=regulatory_requirement,
            policy_document=policy_document,
            **validated_data
        )
    
    def validate_mapping_confidence(self, value):
        """Validate mapping confidence is between 0 and 1"""
        if value is not None and (value < 0.0 or value > 1.0):
            raise serializers.ValidationError("Mapping confidence must be between 0.0 and 1.0")
        return value


class DSARRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for DSARRequest model.
    """
    compliance_run_id = serializers.IntegerField(write_only=True, help_text="ID of the ComplianceRun")
    
    class Meta:
        model = DSARRequest
        fields = [
            'id', 'compliance_run_id', 'request_id', 'request_type', 'data_subject_name',
            'data_subject_email', 'data_subject_id', 'request_date', 'request_description',
            'verification_status', 'status', 'response_due_date', 'response_date',
            'response_method', 'data_sources_searched', 'personal_data_found',
            'data_categories', 'processing_notes', 'rejection_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        compliance_run_id = validated_data.pop('compliance_run_id')
        
        user = self.context['request'].user
        compliance_run = ComplianceRun.objects.get(id=compliance_run_id, run__user=user)
        
        return DSARRequest.objects.create(
            user=user,
            compliance_run=compliance_run,
            **validated_data
        )
    
    def validate_request_id(self, value):
        """Validate request ID is unique"""
        if DSARRequest.objects.filter(request_id=value).exists():
            raise serializers.ValidationError("DSAR request ID must be unique")
        return value


class DataInventorySerializer(serializers.ModelSerializer):
    """
    Serializer for DataInventory model.
    """
    compliance_run_id = serializers.IntegerField(write_only=True, help_text="ID of the ComplianceRun")
    dpia_document_id = serializers.IntegerField(write_only=True, required=False, help_text="ID of the DPIA File")
    
    class Meta:
        model = DataInventory
        fields = [
            'id', 'compliance_run_id', 'activity_name', 'activity_description',
            'data_categories', 'special_categories', 'data_subject_categories',
            'legal_basis', 'processing_purposes', 'data_sources', 'data_recipients',
            'international_transfers', 'transfer_countries', 'transfer_safeguards',
            'retention_period', 'retention_criteria', 'technical_measures',
            'organizational_measures', 'dpia_required', 'dpia_completed',
            'dpia_document_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        compliance_run_id = validated_data.pop('compliance_run_id')
        dpia_document_id = validated_data.pop('dpia_document_id', None)
        
        user = self.context['request'].user
        compliance_run = ComplianceRun.objects.get(id=compliance_run_id, run__user=user)
        
        dpia_document = None
        if dpia_document_id:
            dpia_document = File.objects.get(id=dpia_document_id, user=user)
        
        return DataInventory.objects.create(
            user=user,
            compliance_run=compliance_run,
            dpia_document=dpia_document,
            **validated_data
        )


class RedactionTaskSerializer(serializers.ModelSerializer):
    """
    Serializer for RedactionTask model.
    """
    compliance_run_id = serializers.IntegerField(write_only=True, help_text="ID of the ComplianceRun")
    source_document_id = serializers.IntegerField(write_only=True, help_text="ID of the source File")
    redacted_document_id = serializers.IntegerField(write_only=True, required=False, help_text="ID of the redacted File")
    
    class Meta:
        model = RedactionTask
        fields = [
            'id', 'compliance_run_id', 'task_name', 'source_document_id', 'redaction_type',
            'redaction_rules', 'redaction_patterns', 'status', 'redacted_document_id',
            'redaction_count', 'redaction_summary', 'qa_required', 'qa_completed',
            'qa_reviewer', 'qa_notes', 'processing_metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        compliance_run_id = validated_data.pop('compliance_run_id')
        source_document_id = validated_data.pop('source_document_id')
        redacted_document_id = validated_data.pop('redacted_document_id', None)
        
        user = self.context['request'].user
        compliance_run = ComplianceRun.objects.get(id=compliance_run_id, run__user=user)
        source_document = File.objects.get(id=source_document_id, user=user)
        
        redacted_document = None
        if redacted_document_id:
            redacted_document = File.objects.get(id=redacted_document_id, user=user)
        
        return RedactionTask.objects.create(
            user=user,
            compliance_run=compliance_run,
            source_document=source_document,
            redacted_document=redacted_document,
            **validated_data
        )


class ComplianceAlertSerializer(serializers.ModelSerializer):
    """
    Serializer for ComplianceAlert model.
    """
    compliance_run_id = serializers.IntegerField(write_only=True, help_text="ID of the ComplianceRun")
    related_requirement_id = serializers.IntegerField(write_only=True, required=False, help_text="ID of related RegulatoryRequirement")
    related_dsar_id = serializers.IntegerField(write_only=True, required=False, help_text="ID of related DSARRequest")
    related_document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of related File IDs"
    )
    
    class Meta:
        model = ComplianceAlert
        fields = [
            'id', 'compliance_run_id', 'alert_type', 'alert_title', 'alert_description',
            'severity', 'priority', 'related_requirement_id', 'related_dsar_id',
            'related_document_ids', 'status', 'assigned_to', 'resolution_notes',
            'resolved_at', 'due_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        compliance_run_id = validated_data.pop('compliance_run_id')
        related_requirement_id = validated_data.pop('related_requirement_id', None)
        related_dsar_id = validated_data.pop('related_dsar_id', None)
        related_document_ids = validated_data.pop('related_document_ids', [])
        
        user = self.context['request'].user
        compliance_run = ComplianceRun.objects.get(id=compliance_run_id, run__user=user)
        
        related_requirement = None
        if related_requirement_id:
            related_requirement = RegulatoryRequirement.objects.get(id=related_requirement_id, user=user)
        
        related_dsar = None
        if related_dsar_id:
            related_dsar = DSARRequest.objects.get(id=related_dsar_id, user=user)
        
        alert = ComplianceAlert.objects.create(
            user=user,
            compliance_run=compliance_run,
            related_requirement=related_requirement,
            related_dsar=related_dsar,
            **validated_data
        )
        
        # Add related documents
        if related_document_ids:
            related_docs = File.objects.filter(id__in=related_document_ids, user=user)
            alert.related_documents.set(related_docs)
        
        return alert


# Summary serializers for analytics
class ComplianceSummarySerializer(serializers.Serializer):
    """
    Summary serializer for compliance statistics.
    """
    total_requirements = serializers.IntegerField()
    compliant_requirements = serializers.IntegerField()
    non_compliant_requirements = serializers.IntegerField()
    partially_compliant_requirements = serializers.IntegerField()
    under_review_requirements = serializers.IntegerField()
    
    compliance_rate = serializers.FloatField()
    critical_risks = serializers.IntegerField()
    high_risks = serializers.IntegerField()
    
    category_breakdown = serializers.DictField()
    risk_level_breakdown = serializers.DictField()


class DSARSummarySerializer(serializers.Serializer):
    """
    Summary serializer for DSAR statistics.
    """
    total_requests = serializers.IntegerField()
    completed_requests = serializers.IntegerField()
    overdue_requests = serializers.IntegerField()
    pending_requests = serializers.IntegerField()
    
    avg_response_time = serializers.FloatField()
    request_type_breakdown = serializers.DictField()
    verification_status_breakdown = serializers.DictField()


class RedactionSummarySerializer(serializers.Serializer):
    """
    Summary serializer for redaction task statistics.
    """
    total_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
    failed_tasks = serializers.IntegerField()
    
    total_redactions = serializers.IntegerField()
    redaction_type_breakdown = serializers.DictField()
    qa_completion_rate = serializers.FloatField()


class AlertSummarySerializer(serializers.Serializer):
    """
    Summary serializer for compliance alert statistics.
    """
    total_alerts = serializers.IntegerField()
    open_alerts = serializers.IntegerField()
    critical_alerts = serializers.IntegerField()
    overdue_alerts = serializers.IntegerField()
    
    alert_type_breakdown = serializers.DictField()
    severity_breakdown = serializers.DictField()
    resolution_rate = serializers.FloatField()
