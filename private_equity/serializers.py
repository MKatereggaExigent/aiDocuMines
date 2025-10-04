from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.models import File, Run
from .models import (
    DueDiligenceRun, DocumentClassification, RiskClause, 
    FindingsReport, DataRoomConnector
)

User = get_user_model()


class DueDiligenceRunSerializer(serializers.ModelSerializer):
    """Serializer for DueDiligenceRun model"""
    
    run_id = serializers.UUIDField(source='run.run_id', read_only=True)
    user_email = serializers.EmailField(source='run.user.email', read_only=True)
    total_documents = serializers.SerializerMethodField()
    total_risk_clauses = serializers.SerializerMethodField()
    
    class Meta:
        model = DueDiligenceRun
        fields = [
            'id', 'run_id', 'user_email', 'deal_name', 'target_company',
            'deal_type', 'data_room_source', 'deal_value', 'expected_close_date',
            'total_documents', 'total_risk_clauses', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_documents(self, obj):
        """Get total number of documents in this DD run"""
        return obj.document_classifications.count()
    
    def get_total_risk_clauses(self, obj):
        """Get total number of risk clauses found"""
        return obj.risk_clauses.count()
    
    def validate_deal_value(self, value):
        """Validate deal value is positive"""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Deal value must be positive")
        return value


class DocumentClassificationSerializer(serializers.ModelSerializer):
    """Serializer for DocumentClassification model"""
    
    file_name = serializers.CharField(source='file.filename', read_only=True)
    file_size = serializers.IntegerField(source='file.file_size', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    verified_by_email = serializers.EmailField(source='verified_by.email', read_only=True)
    
    class Meta:
        model = DocumentClassification
        fields = [
            'id', 'file', 'file_name', 'file_size', 'due_diligence_run',
            'document_type', 'document_type_display', 'confidence_score',
            'classification_metadata', 'is_verified', 'verified_by_email',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def validate_confidence_score(self, value):
        """Validate confidence score is between 0 and 1"""
        if not 0.0 <= value <= 1.0:
            raise serializers.ValidationError("Confidence score must be between 0.0 and 1.0")
        return value


class RiskClauseSerializer(serializers.ModelSerializer):
    """Serializer for RiskClause model"""
    
    file_name = serializers.CharField(source='file.filename', read_only=True)
    clause_type_display = serializers.CharField(source='get_clause_type_display', read_only=True)
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True)
    
    class Meta:
        model = RiskClause
        fields = [
            'id', 'file', 'file_name', 'due_diligence_run', 'clause_type',
            'clause_type_display', 'clause_text', 'risk_level', 'risk_level_display',
            'page_number', 'position_start', 'position_end', 'risk_explanation',
            'mitigation_suggestions', 'is_reviewed', 'reviewed_by_email',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def validate_page_number(self, value):
        """Validate page number is positive"""
        if value <= 0:
            raise serializers.ValidationError("Page number must be positive")
        return value
    
    def validate_position_start(self, value):
        """Validate position_start is non-negative"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Position start must be non-negative")
        return value
    
    def validate(self, data):
        """Validate position_end is greater than position_start"""
        position_start = data.get('position_start')
        position_end = data.get('position_end')
        
        if position_start is not None and position_end is not None:
            if position_end <= position_start:
                raise serializers.ValidationError(
                    "Position end must be greater than position start"
                )
        return data


class FindingsReportSerializer(serializers.ModelSerializer):
    """Serializer for FindingsReport model"""
    
    deal_name = serializers.CharField(source='due_diligence_run.deal_name', read_only=True)
    target_company = serializers.CharField(source='due_diligence_run.target_company', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    finalized_by_email = serializers.EmailField(source='finalized_by.email', read_only=True)
    
    class Meta:
        model = FindingsReport
        fields = [
            'id', 'due_diligence_run', 'deal_name', 'target_company',
            'report_name', 'executive_summary', 'document_summary',
            'risk_summary', 'key_findings', 'recommendations',
            'total_documents_reviewed', 'total_risk_clauses_found',
            'high_risk_items_count', 'status', 'status_display',
            'generated_at', 'updated_at', 'finalized_at', 'finalized_by_email'
        ]
        read_only_fields = ['id', 'user', 'generated_at', 'updated_at']
    
    def validate_total_documents_reviewed(self, value):
        """Validate total documents reviewed is non-negative"""
        if value < 0:
            raise serializers.ValidationError("Total documents reviewed must be non-negative")
        return value
    
    def validate_total_risk_clauses_found(self, value):
        """Validate total risk clauses found is non-negative"""
        if value < 0:
            raise serializers.ValidationError("Total risk clauses found must be non-negative")
        return value


class DataRoomConnectorSerializer(serializers.ModelSerializer):
    """Serializer for DataRoomConnector model"""
    
    connector_type_display = serializers.CharField(source='get_connector_type_display', read_only=True)
    sync_status_display = serializers.CharField(source='get_sync_status_display', read_only=True)
    
    class Meta:
        model = DataRoomConnector
        fields = [
            'id', 'due_diligence_run', 'connector_type', 'connector_type_display',
            'connector_name', 'connection_config', 'last_sync_at', 'sync_status',
            'sync_status_display', 'sync_error_message', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'last_sync_at', 'created_at', 'updated_at']
        extra_kwargs = {
            'connection_config': {'write_only': True}  # Don't expose sensitive config in responses
        }
    
    def validate_connector_name(self, value):
        """Validate connector name is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Connector name cannot be empty")
        return value.strip()


class DueDiligenceRunCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new DueDiligenceRun with associated Run"""
    
    class Meta:
        model = DueDiligenceRun
        fields = [
            'deal_name', 'target_company', 'deal_type', 'data_room_source',
            'deal_value', 'expected_close_date'
        ]
    
    def create(self, validated_data):
        """Create a new Run and associated DueDiligenceRun"""
        user = self.context['request'].user
        
        # Create the core Run first
        run = Run.objects.create(
            user=user,
            status='Uploaded'
        )
        
        # Create the DueDiligenceRun
        due_diligence_run = DueDiligenceRun.objects.create(
            run=run,
            **validated_data
        )
        
        return due_diligence_run


class RiskClauseSummarySerializer(serializers.Serializer):
    """Serializer for risk clause summary statistics"""
    
    clause_type = serializers.CharField()
    clause_type_display = serializers.CharField()
    total_count = serializers.IntegerField()
    high_risk_count = serializers.IntegerField()
    medium_risk_count = serializers.IntegerField()
    low_risk_count = serializers.IntegerField()
    critical_risk_count = serializers.IntegerField()


class DocumentTypeSummarySerializer(serializers.Serializer):
    """Serializer for document type summary statistics"""
    
    document_type = serializers.CharField()
    document_type_display = serializers.CharField()
    total_count = serializers.IntegerField()
    verified_count = serializers.IntegerField()
    avg_confidence_score = serializers.FloatField()
