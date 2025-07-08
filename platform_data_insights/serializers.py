# platform_data_insights/serializers.py

from rest_framework import serializers
from .models import UserInsights

class UserInsightsSerializer(serializers.ModelSerializer):
    """
    Serializer for the UserInsights model.
    """

    class Meta:
        model = UserInsights
        fields = [
            "id",
            "user",
            "insights_data",
            "generated_at",
            "generated_async",
            "task_id",
        ]
        read_only_fields = [
            "id",
            "generated_at",
            "generated_async",
            "task_id",
        ]


class InsightsResponseSerializer(serializers.Serializer):
    """
    Serializer for the API response of platform insights.
    """
    cached = serializers.BooleanField()
    generated_at = serializers.DateTimeField()
    insights = serializers.DictField()

