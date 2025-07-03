# file_elasticsearch/serializers.py

from rest_framework import serializers

class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(required=False)
    scope = serializers.ChoiceField(
        choices=["filename", "content", "both"],
        default="both",
        required=False
    )
    user_id = serializers.IntegerField(required=False)
    project_id = serializers.CharField(required=False)
    service_id = serializers.CharField(required=False)

class AdvancedSearchSerializer(serializers.Serializer):
    must = serializers.ListField(
        child=serializers.DictField(), required=False
    )
    filter = serializers.ListField(
        child=serializers.DictField(), required=False
    )

