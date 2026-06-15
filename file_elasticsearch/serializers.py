from rest_framework import serializers


class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(required=False, default="")
    scope = serializers.ChoiceField(
        choices=["filename", "content", "both"],
        default="both",
        required=False,
    )
    page = serializers.IntegerField(default=1, min_value=1, required=False)
    page_size = serializers.IntegerField(default=50, min_value=1, max_value=200, required=False)
    project_id = serializers.CharField(required=False)
    service_id = serializers.CharField(required=False)


class AdvancedSearchSerializer(serializers.Serializer):
    must = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    filter = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    page = serializers.IntegerField(default=1, min_value=1, required=False)
    page_size = serializers.IntegerField(default=50, min_value=1, max_value=200, required=False)
