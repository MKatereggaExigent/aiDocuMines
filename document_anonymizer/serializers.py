from rest_framework import serializers
from .models import AnonymizationRun, Anonymize, DeAnonymize


class AnonymizationRunSerializer(serializers.ModelSerializer):
    """
    Serializes the Anonymization Run details.
    """
    class Meta:
        model = AnonymizationRun
        fields = [
            "id", "project_id", "service_id", "client_name", "status",
            "anonymization_type", "error_message", "created_at", "updated_at"
        ]


class AnonymizeSerializer(serializers.ModelSerializer):
    """
    Serializes the anonymized document details, including HTML, Markdown, and structured outputs.
    """
    class Meta:
        model = Anonymize
        fields = [
            "id", "run", "original_file",
            "anonymized_filepath", "anonymized_html_filepath", "anonymized_markdown_filepath", "anonymized_structured_filepath",
            "entity_mapping_filepath",
            "presidio_masking_map", "spacy_masking_map",
            "status", "created_at", "updated_at"
        ]


class DeAnonymizeSerializer(serializers.ModelSerializer):
    """
    Serializes the de-anonymized document details.
    """
    class Meta:
        model = DeAnonymize
        fields = [
            "id", "file", "unmasked_text", "unmasked_filepath", "status",
            "created_at", "updated_at"
        ]

