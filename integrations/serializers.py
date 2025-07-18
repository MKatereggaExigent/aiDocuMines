# integrations/serializers.py

from rest_framework import serializers
from .models import IntegrationLog

class IntegrationLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = IntegrationLog
        fields = [
            'id',
            'user_email',
            'username',
            'connector',
            'status',
            'details',
            'autologin_url',
            'timestamp',
        ]
        read_only_fields = fields

