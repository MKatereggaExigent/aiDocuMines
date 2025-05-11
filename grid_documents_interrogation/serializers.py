from rest_framework import serializers
from .models import Topic, Query
from core.models import File  # Assuming File is in core.models
from django.contrib.auth import get_user_model

User = get_user_model()

class TopicSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    project_id = serializers.CharField()
    service_id = serializers.CharField()

    class Meta:
        model = Topic
        fields = [
            'id',
            'name',
            'project_id',
            'service_id',
            'user',
            'chat_date'
        ]
        read_only_fields = ['id', 'user', 'chat_date']


class QuerySerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    topic = serializers.PrimaryKeyRelatedField(queryset=Topic.objects.all())
    file = serializers.PrimaryKeyRelatedField(queryset=File.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Query
        fields = [
            'id',
            'topic',
            'user',
            'file',
            'query_text',
            'response_text',
            'created_at',
        ]
        read_only_fields = ['id', 'user', 'created_at']

