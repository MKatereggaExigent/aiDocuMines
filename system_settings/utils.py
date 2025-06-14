# system_settings/utils.py

from typing import Dict, Any
import logging
from .models import SystemSettings
from custom_authentication.models import Client
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)


# system_settings/utils.py

def get_default_settings_schema():
    return {
        "site_name": "string",
        "default_language": ["en", "fr"],
        "dark_mode": "boolean",
        "maintenance_mode": "boolean",
        "public_registration": "boolean",
        "password_pattern": "string",
        "password_expiry_days": "integer",
        "session_timeout": "integer",
        "enforce_2fa": "boolean",
        "email_verification": "boolean",
        "api_rate_limit": "integer",
        "disable_file_downloads": "boolean",
        "enable_gdpr_mode": "boolean",
        "log_data_access": "boolean",
        "redact_logs": "boolean",
        "smtp_host": "string",
        "smtp_port": "integer",
        "from_email": "email",
        "admin_email": "email",
        "notify_enabled": "boolean",
        "openai_api_key": "string",
        "azure_storage_key": "string",
        "slack_webhook": "url",
        "oauth_client_id": "string",
        "oauth_client_secret": "string",
        "backup_frequency": ["daily", "weekly", "monthly"],
        "backup_retention": "integer",
        "encrypt_backups": "boolean",
        "enable_logging": "boolean",
        "log_retention": "integer",
        "log_level": ["debug", "info", "warn", "error"],
        "send_logs_to_admin": "boolean",
        "default_role": "string",
        "disable_self_delete": "boolean",
        "max_users": "integer",
        "require_role_approval": "boolean",
        "allow_file_upload": "boolean",
        "max_upload_mb": "integer",
        "allowed_file_types": "string",
        "default_timezone": "string",
        "enable_iso_logging": "boolean",
        "enable_hipaa_mode": "boolean",
        "enable_audit_log_download": "boolean",
    }

def get_default_settings_values():
    return {
        "site_name": "AI DocuMines",
        "default_language": "en",
        "dark_mode": True,
        "maintenance_mode": False,
        "public_registration": True,
        "password_pattern": "",
        "password_expiry_days": 90,
        "session_timeout": 30,
        "enforce_2fa": False,
        "email_verification": True,
        "api_rate_limit": 60,
        "disable_file_downloads": False,
        "enable_gdpr_mode": True,
        "log_data_access": True,
        "redact_logs": False,
        "smtp_host": "",
        "smtp_port": 587,
        "from_email": "",
        "admin_email": "",
        "notify_enabled": True,
        "openai_api_key": "",
        "azure_storage_key": "",
        "slack_webhook": "",
        "oauth_client_id": "",
        "oauth_client_secret": "",
        "backup_frequency": "daily",
        "backup_retention": 30,
        "encrypt_backups": True,
        "enable_logging": True,
        "log_retention": 90,
        "log_level": "info",
        "send_logs_to_admin": False,
        "default_role": "User",
        "disable_self_delete": False,
        "max_users": 100,
        "require_role_approval": True,
        "allow_file_upload": True,
        "max_upload_mb": 100,
        "allowed_file_types": ".pdf,.docx,.xlsx",
        "default_timezone": "UTC",
        "enable_iso_logging": False,
        "enable_hipaa_mode": False,
        "enable_audit_log_download": True,
    }



def validate_system_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clean incoming system settings.
    """
    cleaned = {}
    try:
        cleaned['site_name'] = str(data.get('site_name', 'Platform'))
        cleaned['default_language'] = data.get('default_language', 'en')
        cleaned['dark_mode'] = bool(data.get('dark_mode', False))
        cleaned['maintenance_mode'] = bool(data.get('maintenance_mode', False))
        cleaned['public_registration'] = bool(data.get('public_registration', True))

        # Security
        cleaned['password_pattern'] = str(data.get('password_pattern', ''))
        cleaned['password_expiry_days'] = int(data.get('password_expiry_days', 90))
        cleaned['session_timeout'] = int(data.get('session_timeout', 30))
        cleaned['enforce_2fa'] = bool(data.get('enforce_2fa', False))
        cleaned['email_verification'] = bool(data.get('email_verification', True))
        cleaned['api_rate_limit'] = str(data.get('api_rate_limit', '60'))
        cleaned['disable_file_downloads'] = bool(data.get('disable_file_downloads', False))

        # Privacy
        cleaned['enable_gdpr_mode'] = bool(data.get('enable_gdpr_mode', False))
        cleaned['log_data_access'] = bool(data.get('log_data_access', False))
        cleaned['redact_logs'] = bool(data.get('redact_logs', False))

        # Email
        cleaned['smtp_host'] = str(data.get('smtp_host', ''))
        cleaned['smtp_port'] = int(data.get('smtp_port', 587))
        cleaned['from_email'] = str(data.get('from_email', 'admin@example.com'))
        cleaned['admin_email'] = str(data.get('admin_email', 'admin@example.com'))
        cleaned['notify_enabled'] = bool(data.get('notify_enabled', True))

        # Integrations
        cleaned['openai_api_key'] = str(data.get('openai_api_key', ''))
        cleaned['azure_storage_key'] = str(data.get('azure_storage_key', ''))
        cleaned['slack_webhook'] = str(data.get('slack_webhook', ''))
        cleaned['oauth_client_id'] = str(data.get('oauth_client_id', ''))
        cleaned['oauth_client_secret'] = str(data.get('oauth_client_secret', ''))

        # Backups
        cleaned['backup_frequency'] = data.get('backup_frequency', 'weekly')
        cleaned['backup_retention'] = int(data.get('backup_retention', 30))
        cleaned['encrypt_backups'] = bool(data.get('encrypt_backups', True))

        # Logging
        cleaned['enable_logging'] = bool(data.get('enable_logging', True))
        cleaned['log_retention'] = int(data.get('log_retention', 30))
        cleaned['log_level'] = data.get('log_level', 'info')
        cleaned['send_logs_to_admin'] = bool(data.get('send_logs_to_admin', False))

        # User management
        cleaned['default_role'] = str(data.get('default_role', 'user'))
        cleaned['disable_self_delete'] = bool(data.get('disable_self_delete', False))
        cleaned['max_users'] = int(data.get('max_users', 100))
        cleaned['require_role_approval'] = bool(data.get('require_role_approval', False))

        # File handling
        cleaned['allow_file_upload'] = bool(data.get('allow_file_upload', True))
        cleaned['max_upload_mb'] = int(data.get('max_upload_mb', 25))
        cleaned['allowed_file_types'] = str(data.get('allowed_file_types', '.pdf,.docx,.xlsx'))
        cleaned['default_timezone'] = str(data.get('default_timezone', 'UTC'))

        # Compliance
        cleaned['enable_iso_logging'] = bool(data.get('enable_iso_logging', False))
        cleaned['enable_hipaa_mode'] = bool(data.get('enable_hipaa_mode', False))
        cleaned['enable_audit_log_download'] = bool(data.get('enable_audit_log_download', False))

    except Exception as e:
        logger.exception("System settings validation failed: %s", str(e))
        raise ValueError("Invalid system settings format")

    return cleaned


def save_settings_to_database(client_id: int, settings: Dict[str, Any]) -> SystemSettings:
    """
    Save or update settings for a given client in the database.
    """
    try:
        client = Client.objects.get(id=client_id)
    except ObjectDoesNotExist:
        raise ValueError("Client does not exist")

    validated = validate_system_settings(settings)

    instance, _ = SystemSettings.objects.update_or_create(
        client=client,
        defaults=validated
    )
    logger.info("System settings saved for client: %s", client.name)
    return instance
