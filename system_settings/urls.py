from django.urls import path
from .views import (
    SystemSettingsView,
    SystemSettingsResetView,
    SystemSettingsAuditTrailView,
    SystemSettingsSchemaView
)

urlpatterns = [
    path("auth/admin/system-settings/", SystemSettingsView.as_view(), name="system_settings_get"),
    path("auth/admin/system-settings/update/", SystemSettingsView.as_view(), name="system_settings_post"),
    path("auth/admin/system-settings/reset/", SystemSettingsResetView.as_view(), name="system_settings_reset"),
    path("auth/admin/system-settings/audit/", SystemSettingsAuditTrailView.as_view(), name="system_settings_audit"),
    path("auth/admin/system-settings/schema/", SystemSettingsSchemaView.as_view(), name="system_settings_schema"),
]

