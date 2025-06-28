# document_search/serializers.py

from rest_framework import serializers
from document_search.models import VectorChunk


#class VectorChunkSerializer(serializers.ModelSerializer):
#    class Meta:
#        model = VectorChunk
#        fields = ['id', 'file', 'chunk_index', 'chunk_text', 'created_at']


class VectorChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = VectorChunk
        fields = [
            'id',
            'file',
            'chunk_index',
            'chunk_text',
            'chunk_hash',       # ✅ add this line
            'created_at',
        ]
        extra_kwargs = {
            'chunk_hash': {'read_only': True},  # ✅ optional: prevent client from setting it
        }


class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=1000)
    file_id = serializers.IntegerField(required=False)
    top_k = serializers.IntegerField(default=5, min_value=1, max_value=50)


class SearchResultSerializer(serializers.Serializer):
    file_id = serializers.IntegerField()
    file_name = serializers.CharField()
    chunk_text = serializers.CharField()
    score = serializers.FloatField()

class IndexRequestSerializer(serializers.Serializer):
    """
    POST /document-search/index/
    {
        "file_ids": [1, 2, 3],
        "force": false
    }
    """
    file_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False
    )
    force = serializers.BooleanField(default=False)

class AsyncSearchResponse(serializers.Serializer):
    task_id  = serializers.CharField()

