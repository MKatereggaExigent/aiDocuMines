from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.models import Run, File
from .models import (
    PatentAnalysisRun, PatentDocument, PatentClaim, PriorArtDocument,
    ClaimChart, PatentLandscape, InfringementAnalysis, ValidityChallenge
)

User = get_user_model()


class PatentAnalysisRunSerializer(serializers.ModelSerializer):
    """
    Serializer for PatentAnalysisRun model.
    """
    run_id = serializers.IntegerField(write_only=True, help_text="ID of the core Run to associate with")
    
    class Meta:
        model = PatentAnalysisRun
        fields = [
            'id', 'run_id', 'case_name', 'litigation_type', 'patent_sources',
            'patents_in_suit', 'technology_area', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        run_id = validated_data.pop('run_id')
        run = Run.objects.get(id=run_id, user=self.context['request'].user)
        return PatentAnalysisRun.objects.create(run=run, **validated_data)
    
    def validate_patents_in_suit(self, value):
        """Validate patents in suit format"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Patents in suit must be a list")
        
        for patent in value:
            if not isinstance(patent, str) or len(patent.strip()) == 0:
                raise serializers.ValidationError("Each patent number must be a non-empty string")
        
        return value


class PatentDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for PatentDocument model.
    """
    file_id = serializers.IntegerField(write_only=True, help_text="ID of the File containing patent document")
    analysis_run_id = serializers.IntegerField(write_only=True, help_text="ID of the PatentAnalysisRun")
    
    class Meta:
        model = PatentDocument
        fields = [
            'id', 'file_id', 'analysis_run_id', 'patent_number', 'application_number',
            'publication_number', 'patent_office', 'title', 'inventors', 'assignees',
            'filing_date', 'publication_date', 'grant_date', 'expiration_date',
            'status', 'ipc_classes', 'cpc_classes', 'abstract', 'claims_text',
            'description_text', 'processing_metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        file_id = validated_data.pop('file_id')
        analysis_run_id = validated_data.pop('analysis_run_id')
        
        user = self.context['request'].user
        file_obj = File.objects.get(id=file_id, user=user)
        analysis_run = PatentAnalysisRun.objects.get(id=analysis_run_id, run__user=user)
        
        return PatentDocument.objects.create(
            file=file_obj,
            user=user,
            analysis_run=analysis_run,
            **validated_data
        )
    
    def validate_patent_number(self, value):
        """Validate patent number format"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Patent number is required")
        return value.strip().upper()


class PatentClaimSerializer(serializers.ModelSerializer):
    """
    Serializer for PatentClaim model.
    """
    patent_document_id = serializers.IntegerField(write_only=True, help_text="ID of the PatentDocument")
    analysis_run_id = serializers.IntegerField(write_only=True, help_text="ID of the PatentAnalysisRun")
    
    class Meta:
        model = PatentClaim
        fields = [
            'id', 'patent_document_id', 'analysis_run_id', 'claim_number', 'claim_text',
            'claim_type', 'depends_on_claims', 'claim_elements', 'element_count',
            'complexity_score', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        patent_document_id = validated_data.pop('patent_document_id')
        analysis_run_id = validated_data.pop('analysis_run_id')
        
        user = self.context['request'].user
        patent_document = PatentDocument.objects.get(id=patent_document_id, user=user)
        analysis_run = PatentAnalysisRun.objects.get(id=analysis_run_id, run__user=user)
        
        return PatentClaim.objects.create(
            patent_document=patent_document,
            user=user,
            analysis_run=analysis_run,
            **validated_data
        )
    
    def validate_claim_number(self, value):
        """Validate claim number is positive"""
        if value <= 0:
            raise serializers.ValidationError("Claim number must be positive")
        return value


class PriorArtDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for PriorArtDocument model.
    """
    file_id = serializers.IntegerField(write_only=True, help_text="ID of the File containing prior art document")
    analysis_run_id = serializers.IntegerField(write_only=True, help_text="ID of the PatentAnalysisRun")
    
    class Meta:
        model = PriorArtDocument
        fields = [
            'id', 'file_id', 'analysis_run_id', 'document_id', 'document_type',
            'title', 'authors', 'publication_date', 'source', 'abstract',
            'content_text', 'relevance_score', 'relevance_explanation',
            'art_categories', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        file_id = validated_data.pop('file_id')
        analysis_run_id = validated_data.pop('analysis_run_id')
        
        user = self.context['request'].user
        file_obj = File.objects.get(id=file_id, user=user)
        analysis_run = PatentAnalysisRun.objects.get(id=analysis_run_id, run__user=user)
        
        return PriorArtDocument.objects.create(
            file=file_obj,
            user=user,
            analysis_run=analysis_run,
            **validated_data
        )
    
    def validate_relevance_score(self, value):
        """Validate relevance score is between 0 and 1"""
        if value is not None and (value < 0.0 or value > 1.0):
            raise serializers.ValidationError("Relevance score must be between 0.0 and 1.0")
        return value


class ClaimChartSerializer(serializers.ModelSerializer):
    """
    Serializer for ClaimChart model.
    """
    analysis_run_id = serializers.IntegerField(write_only=True, help_text="ID of the PatentAnalysisRun")
    patent_claim_id = serializers.IntegerField(write_only=True, help_text="ID of the PatentClaim")
    target_prior_art_id = serializers.IntegerField(write_only=True, required=False, help_text="ID of the PriorArtDocument")
    supporting_document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of File IDs for supporting documents"
    )
    
    class Meta:
        model = ClaimChart
        fields = [
            'id', 'analysis_run_id', 'patent_claim_id', 'chart_name', 'chart_type',
            'target_product', 'target_prior_art_id', 'element_mappings',
            'overall_conclusion', 'confidence_score', 'analysis_notes',
            'supporting_document_ids', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        analysis_run_id = validated_data.pop('analysis_run_id')
        patent_claim_id = validated_data.pop('patent_claim_id')
        target_prior_art_id = validated_data.pop('target_prior_art_id', None)
        supporting_document_ids = validated_data.pop('supporting_document_ids', [])
        
        user = self.context['request'].user
        analysis_run = PatentAnalysisRun.objects.get(id=analysis_run_id, run__user=user)
        patent_claim = PatentClaim.objects.get(id=patent_claim_id, user=user)
        
        target_prior_art = None
        if target_prior_art_id:
            target_prior_art = PriorArtDocument.objects.get(id=target_prior_art_id, user=user)
        
        claim_chart = ClaimChart.objects.create(
            user=user,
            analysis_run=analysis_run,
            patent_claim=patent_claim,
            target_prior_art=target_prior_art,
            **validated_data
        )
        
        # Add supporting documents
        if supporting_document_ids:
            supporting_docs = File.objects.filter(id__in=supporting_document_ids, user=user)
            claim_chart.supporting_documents.set(supporting_docs)
        
        return claim_chart
    
    def validate_confidence_score(self, value):
        """Validate confidence score is between 0 and 1"""
        if value is not None and (value < 0.0 or value > 1.0):
            raise serializers.ValidationError("Confidence score must be between 0.0 and 1.0")
        return value


class PatentLandscapeSerializer(serializers.ModelSerializer):
    """
    Serializer for PatentLandscape model.
    """
    analysis_run_id = serializers.IntegerField(write_only=True, help_text="ID of the PatentAnalysisRun")
    
    class Meta:
        model = PatentLandscape
        fields = [
            'id', 'analysis_run_id', 'landscape_name', 'technology_area',
            'search_keywords', 'classification_codes', 'date_range_start',
            'date_range_end', 'total_patents_found', 'key_players',
            'technology_trends', 'patent_clusters', 'landscape_metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        analysis_run_id = validated_data.pop('analysis_run_id')
        
        user = self.context['request'].user
        analysis_run = PatentAnalysisRun.objects.get(id=analysis_run_id, run__user=user)
        
        return PatentLandscape.objects.create(
            user=user,
            analysis_run=analysis_run,
            **validated_data
        )


class InfringementAnalysisSerializer(serializers.ModelSerializer):
    """
    Serializer for InfringementAnalysis model.
    """
    analysis_run_id = serializers.IntegerField(write_only=True, help_text="ID of the PatentAnalysisRun")
    asserted_patent_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        help_text="List of PatentDocument IDs being asserted"
    )
    
    class Meta:
        model = InfringementAnalysis
        fields = [
            'id', 'analysis_run_id', 'analysis_name', 'accused_product',
            'asserted_patent_ids', 'analysis_methodology', 'literal_infringement',
            'doctrine_of_equivalents', 'infringement_conclusion', 'confidence_level',
            'detailed_findings', 'recommendations', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        analysis_run_id = validated_data.pop('analysis_run_id')
        asserted_patent_ids = validated_data.pop('asserted_patent_ids')
        
        user = self.context['request'].user
        analysis_run = PatentAnalysisRun.objects.get(id=analysis_run_id, run__user=user)
        
        infringement_analysis = InfringementAnalysis.objects.create(
            user=user,
            analysis_run=analysis_run,
            **validated_data
        )
        
        # Add asserted patents
        asserted_patents = PatentDocument.objects.filter(id__in=asserted_patent_ids, user=user)
        infringement_analysis.asserted_patents.set(asserted_patents)
        
        return infringement_analysis


class ValidityChallengeSerializer(serializers.ModelSerializer):
    """
    Serializer for ValidityChallenge model.
    """
    analysis_run_id = serializers.IntegerField(write_only=True, help_text="ID of the PatentAnalysisRun")
    target_patent_id = serializers.IntegerField(write_only=True, help_text="ID of the target PatentDocument")
    prior_art_reference_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        help_text="List of PriorArtDocument IDs"
    )
    
    class Meta:
        model = ValidityChallenge
        fields = [
            'id', 'analysis_run_id', 'target_patent_id', 'challenge_name',
            'challenge_grounds', 'prior_art_reference_ids', 'anticipation_analysis',
            'obviousness_analysis', 'challenge_strength', 'success_likelihood',
            'detailed_analysis', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        analysis_run_id = validated_data.pop('analysis_run_id')
        target_patent_id = validated_data.pop('target_patent_id')
        prior_art_reference_ids = validated_data.pop('prior_art_reference_ids')
        
        user = self.context['request'].user
        analysis_run = PatentAnalysisRun.objects.get(id=analysis_run_id, run__user=user)
        target_patent = PatentDocument.objects.get(id=target_patent_id, user=user)
        
        validity_challenge = ValidityChallenge.objects.create(
            user=user,
            analysis_run=analysis_run,
            target_patent=target_patent,
            **validated_data
        )
        
        # Add prior art references
        prior_art_refs = PriorArtDocument.objects.filter(id__in=prior_art_reference_ids, user=user)
        validity_challenge.prior_art_references.set(prior_art_refs)
        
        return validity_challenge
    
    def validate_success_likelihood(self, value):
        """Validate success likelihood is between 0 and 1"""
        if value is not None and (value < 0.0 or value > 1.0):
            raise serializers.ValidationError("Success likelihood must be between 0.0 and 1.0")
        return value


# Summary serializers for analytics
class PatentAnalysisSummarySerializer(serializers.Serializer):
    """
    Summary serializer for patent analysis statistics.
    """
    total_patents = serializers.IntegerField()
    total_claims = serializers.IntegerField()
    total_prior_art = serializers.IntegerField()
    total_claim_charts = serializers.IntegerField()
    infringement_analyses = serializers.IntegerField()
    validity_challenges = serializers.IntegerField()
    
    patent_office_breakdown = serializers.DictField()
    litigation_type_breakdown = serializers.DictField()
    technology_area_breakdown = serializers.DictField()


class ClaimChartSummarySerializer(serializers.Serializer):
    """
    Summary serializer for claim chart statistics.
    """
    chart_type = serializers.CharField()
    chart_type_display = serializers.CharField()
    total_count = serializers.IntegerField()
    infringes_count = serializers.IntegerField()
    does_not_infringe_count = serializers.IntegerField()
    unclear_count = serializers.IntegerField()
    avg_confidence_score = serializers.FloatField()


class InfringementSummarySerializer(serializers.Serializer):
    """
    Summary serializer for infringement analysis statistics.
    """
    total_analyses = serializers.IntegerField()
    infringement_found = serializers.IntegerField()
    no_infringement = serializers.IntegerField()
    mixed_results = serializers.IntegerField()
    inconclusive = serializers.IntegerField()
    
    literal_infringement_rate = serializers.FloatField()
    doe_infringement_rate = serializers.FloatField()
    high_confidence_analyses = serializers.IntegerField()


class ValiditySummarySerializer(serializers.Serializer):
    """
    Summary serializer for validity challenge statistics.
    """
    total_challenges = serializers.IntegerField()
    strong_challenges = serializers.IntegerField()
    moderate_challenges = serializers.IntegerField()
    weak_challenges = serializers.IntegerField()
    
    avg_success_likelihood = serializers.FloatField()
    anticipation_challenges = serializers.IntegerField()
    obviousness_challenges = serializers.IntegerField()
    most_challenged_patents = serializers.ListField()
