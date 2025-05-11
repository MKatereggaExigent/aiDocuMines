from rest_framework import serializers
from document_translation.models import TranslationRun, TranslationFile, TranslationLanguage, TranslationStorage


class TranslationRunSerializer(serializers.ModelSerializer):
    """
    Serializes a translation run, tracking its status.
    """

    class Meta:
        model = TranslationRun
        fields = [
            "id",
            "project_id",
            "service_id",
            "client_name",
            "from_language",
            "to_language",
            "status",
            "created_at",
            "updated_at",
            "error_message",
        ]


class TranslationFileSerializer(serializers.ModelSerializer):
    """
    Serializes translation file details, linking to a `TranslationRun` instance.
    """

    class Meta:
        model = TranslationFile
        fields = [
            "id",
            "run",
            "original_file",
            "translated_filepath",
            "status",
            "created_at",
            "updated_at",
        ]


class TranslationLanguageSerializer(serializers.ModelSerializer):
    """
    Serializes supported languages for translation.
    """

    class Meta:
        model = TranslationLanguage
        fields = ["id", "name", "code"]


class TranslationStorageSerializer(serializers.ModelSerializer):
    """
    Serializes storage details for uploaded and translated files.
    """

    class Meta:
        model = TranslationStorage
        fields = ["storage_id", "run", "upload_storage_location", "translated_storage_location"]
