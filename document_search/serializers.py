from rest_framework import serializers
from document_search.models import VectorChunk


class VectorChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = VectorChunk
        fields = ["id", "file", "chunk_index", "chunk_text", "chunk_hash", "created_at"]
        extra_kwargs = {"chunk_hash": {"read_only": True}}


class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=1000)
    file_id = serializers.IntegerField(required=False)
    top_k = serializers.IntegerField(default=10, min_value=1, max_value=200)
    page = serializers.IntegerField(default=1, min_value=1, required=False)
    page_size = serializers.IntegerField(default=10, min_value=1, max_value=200, required=False)


class SearchResultSerializer(serializers.Serializer):
    file_id = serializers.IntegerField()
    file_name = serializers.CharField()
    chunk_text = serializers.CharField()
    score = serializers.FloatField()


class IndexRequestSerializer(serializers.Serializer):
    file_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False)
    force = serializers.BooleanField(default=False)


class AsyncSearchResponse(serializers.Serializer):
    task_id = serializers.CharField()
