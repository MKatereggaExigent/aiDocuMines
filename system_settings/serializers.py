# system_settings/serializers.py

from rest_framework import serializers
from .models import SystemSettings
from custom_authentication.models import Client

class SystemSettingsSerializer(serializers.ModelSerializer):
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source='client',
        required=True,
        write_only=True
    )
    client_name = serializers.CharField(
        source='client.name',
        read_only=True
    )

    class Meta:
        model = SystemSettings
        fields = [
            # Identifiers
            'id', 'client_id', 'client_name',

            # PLATFORM CONFIG
            'site_name', 'default_language', 'dark_mode',
            'maintenance_mode', 'public_registration',

            # SECURITY
            'password_pattern', 'password_expiry_days',
            'session_timeout', 'enforce_2fa', 'email_verification',
            'api_rate_limit', 'disable_file_downloads',

            # DATA PROTECTION
            'enable_gdpr_mode', 'log_data_access', 'redact_logs',

            # EMAIL & NOTIFICATIONS
            'smtp_host', 'smtp_port', 'from_email', 'admin_email',
            'notify_enabled',

            # INTEGRATIONS
            'openai_api_key', 'azure_storage_key', 'slack_webhook',
            'oauth_client_id', 'oauth_client_secret',

            # BACKUP SETTINGS
            'backup_frequency', 'backup_retention', 'encrypt_backups',

            # LOGGING
            'enable_logging', 'log_retention', 'log_level',
            'send_logs_to_admin',

            # USER MANAGEMENT
            'default_role', 'disable_self_delete', 'max_users',
            'require_role_approval',

            # FILE POLICIES
            'allow_file_upload', 'max_upload_mb', 'allowed_file_types',
            'default_timezone',

            # COMPLIANCE
            'enable_iso_logging', 'enable_hipaa_mode', 'enable_audit_log_download',

            # Metadata
            'updated_at'
        ]
        read_only_fields = ['id', 'updated_at', 'client_name']

